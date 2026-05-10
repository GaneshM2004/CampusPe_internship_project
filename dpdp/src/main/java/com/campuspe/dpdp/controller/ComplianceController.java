package com.campuspe.dpdp.controller;

import com.campuspe.dpdp.model.ComplianceRecord;
import com.campuspe.dpdp.model.User;
import com.campuspe.dpdp.repository.UserRepository;
import com.campuspe.dpdp.service.ComplianceService;
import com.campuspe.dpdp.service.AiServiceClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/records")
public class ComplianceController {

    @Autowired
    private ComplianceService complianceService;

    @Autowired
    private AiServiceClient aiServiceClient;

    @Autowired
    private UserRepository userRepository;

    /**
     * POST /api/records — create a new record, attaching the logged-in user.
     */
    @PostMapping
    public ComplianceRecord submitRecord(@RequestBody Map<String, String> payload,
                                         Authentication authentication) {
        String rawInput = payload.get("rawInput");
        Long userId = (Long) authentication.getDetails();
        User user = userRepository.findById(userId).orElseThrow();
        return complianceService.createRecord(rawInput, user);
    }

    /**
     * GET /api/records — ADMIN sees all records, USER sees only their own.
     */
    @GetMapping
    public List<ComplianceRecord> getRecords(Authentication authentication) {
        boolean isAdmin = authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .anyMatch(a -> a.equals("ROLE_ADMIN"));

        if (isAdmin) {
            return complianceService.getAllRecords();
        } else {
            Long userId = (Long) authentication.getDetails();
            return complianceService.getRecordsByUserId(userId);
        }
    }

    // React will call this when you click "Get Recommendations"
    @GetMapping("/{id}/recommendations")
    public ResponseEntity<?> getRecordRecommendations(@PathVariable Long id) {
        ComplianceRecord record = complianceService.getRecordById(id);
        if (record == null) return ResponseEntity.notFound().build();

        List<Map<String, String>> recommendations = aiServiceClient.getRecommendations(record.getRawInput());
        return ResponseEntity.ok(recommendations);
    }

    // React will call this when you click "Generate Full Report"
    @GetMapping("/{id}/report")
    public ResponseEntity<?> getRecordReport(@PathVariable Long id) {
        ComplianceRecord record = complianceService.getRecordById(id);
        if (record == null) return ResponseEntity.notFound().build();

        Map<String, Object> report = aiServiceClient.generateReport(record.getRawInput());
        return ResponseEntity.ok(report);
    }

    // Day 9 CSV Export Feature — Admin only (enforced on frontend, open for API)
    @GetMapping("/export")
    public ResponseEntity<String> exportToCSV() {
        List<ComplianceRecord> records = complianceService.getAllRecords();
        StringBuilder csv = new StringBuilder("ID,Status,Submitted By,Raw Input,DPO Summary\n");
        
        for (ComplianceRecord record : records) {
            String cleanInput = record.getRawInput() != null ? record.getRawInput().replace("\"", "\"\"") : "";
            String cleanSummary = record.getProfessionalDescription() != null ? record.getProfessionalDescription().replace("\"", "\"\"") : "";
            String submittedBy = record.getSubmittedBy() != null ? record.getSubmittedBy() : "system";
            
            csv.append(record.getId()).append(",")
               .append(record.getStatus()).append(",")
               .append(submittedBy).append(",")
               .append("\"").append(cleanInput).append("\",")
               .append("\"").append(cleanSummary).append("\"\n");
        }
        
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"dpdp_audit_log.csv\"")
                .header(HttpHeaders.CONTENT_TYPE, "text/csv")
                .body(csv.toString());
    }
}
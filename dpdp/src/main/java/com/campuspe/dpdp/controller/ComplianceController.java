package com.campuspe.dpdp.controller;

import com.campuspe.dpdp.model.ComplianceRecord;
import com.campuspe.dpdp.service.ComplianceService;
import com.campuspe.dpdp.service.AiServiceClient; // NEW IMPORT
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity; // NEW IMPORT
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/records")
@CrossOrigin(origins = "*")
public class ComplianceController {

    @Autowired
    private ComplianceService complianceService;

    @Autowired
    private AiServiceClient aiServiceClient; // INJECT THE AI CLIENT

    @PostMapping
    public ComplianceRecord submitRecord(@RequestBody Map<String, String> payload) {
        String rawInput = payload.get("rawInput");
        return complianceService.createRecord(rawInput);
    }

    @GetMapping
    public List<ComplianceRecord> getAllRecords() {
        return complianceService.getAllRecords();
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
    //Day 9 CSV Export Feature
    @GetMapping("/export")
    public ResponseEntity<String> exportToCSV() {
        List<ComplianceRecord> records = complianceService.getAllRecords();
        StringBuilder csv = new StringBuilder("ID,Status,Raw Input,DPO Summary\n");
        
        for (ComplianceRecord record : records) {
            String cleanInput = record.getRawInput() != null ? record.getRawInput().replace("\"", "\"\"") : "";
            String cleanSummary = record.getProfessionalDescription() != null ? record.getProfessionalDescription().replace("\"", "\"\"") : "";
            
            csv.append(record.getId()).append(",")
               .append(record.getStatus()).append(",")
               .append("\"").append(cleanInput).append("\",")
               .append("\"").append(cleanSummary).append("\"\n");
        }
        
        return org.springframework.http.ResponseEntity.ok()
                .header(org.springframework.http.HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"dpdp_audit_log.csv\"")
                .header(org.springframework.http.HttpHeaders.CONTENT_TYPE, "text/csv")
                .body(csv.toString());
    }
}
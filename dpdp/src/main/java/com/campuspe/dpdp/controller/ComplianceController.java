package com.campuspe.dpdp.controller;

import com.campuspe.dpdp.model.ComplianceRecord;
import com.campuspe.dpdp.model.User;
import com.campuspe.dpdp.repository.UserRepository;
import com.campuspe.dpdp.service.ComplianceService;
import com.campuspe.dpdp.service.AiServiceClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
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

    // ── Helper: extract userId from JWT details ───────────────────────────────
    private Long extractUserId(Authentication authentication) {
        Object details = authentication.getDetails();
        if (details instanceof Number) {
            return ((Number) details).longValue();
        }
        throw new IllegalStateException("Cannot extract userId from authentication details");
    }

    // ── Helper: check admin role ──────────────────────────────────────────────
    private boolean isAdmin(Authentication authentication) {
        return authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .anyMatch(a -> a.equals("ROLE_ADMIN"));
    }

    /**
     * POST /api/records — create a new record, attaching the logged-in user.
     */
    @PostMapping
    public ComplianceRecord submitRecord(@RequestBody Map<String, String> payload,
                                         Authentication authentication) {
        String rawInput = payload.get("rawInput");
        if (rawInput == null || rawInput.isBlank()) {
            throw new IllegalArgumentException("rawInput must not be blank");
        }
        Long userId = extractUserId(authentication);
        User user = userRepository.findById(userId).orElseThrow();
        return complianceService.createRecord(rawInput, user);
    }

    /**
     * GET /api/records — ADMIN sees all records, USER sees only their own.
     */
    @GetMapping
    public List<ComplianceRecord> getRecords(Authentication authentication) {
        if (isAdmin(authentication)) {
            return complianceService.getAllRecords();
        } else {
            Long userId = extractUserId(authentication);
            return complianceService.getRecordsByUserId(userId);
        }
    }

    /**
     * GET /api/records/{id}/recommendations
     * Returns AI recommendations for a record.
     * Users can only fetch recommendations for their own records; admins see all.
     */
    @GetMapping("/{id}/recommendations")
    public ResponseEntity<?> getRecordRecommendations(@PathVariable Long id,
                                                       Authentication authentication) {
        ComplianceRecord record = complianceService.getRecordById(id);
        if (record == null) {
            return ResponseEntity.notFound().build();
        }

        // Authorization: non-admins can only access their own records
        if (!isAdmin(authentication)) {
            Long requestingUserId = extractUserId(authentication);
            Long ownerUserId = (record.getUser() != null) ? record.getUser().getId() : null;
            if (!requestingUserId.equals(ownerUserId)) {
                return ResponseEntity.status(HttpStatus.FORBIDDEN)
                        .body(Map.of("error", "Access denied: you do not own this record"));
            }
        }

        List<Map<String, String>> recommendations = aiServiceClient.getRecommendations(record.getRawInput());
        if (recommendations == null) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                    .body(Map.of("error", "AI service temporarily unavailable"));
        }
        return ResponseEntity.ok(recommendations);
    }

    /**
     * GET /api/records/{id}/report
     * Generates a full audit report for a record.
     * Users can only fetch reports for their own records; admins see all.
     */
    @GetMapping("/{id}/report")
    public ResponseEntity<?> getRecordReport(@PathVariable Long id,
                                              Authentication authentication) {
        ComplianceRecord record = complianceService.getRecordById(id);
        if (record == null) {
            return ResponseEntity.notFound().build();
        }

        // Authorization: non-admins can only access their own records
        if (!isAdmin(authentication)) {
            Long requestingUserId = extractUserId(authentication);
            Long ownerUserId = (record.getUser() != null) ? record.getUser().getId() : null;
            if (!requestingUserId.equals(ownerUserId)) {
                return ResponseEntity.status(HttpStatus.FORBIDDEN)
                        .body(Map.of("error", "Access denied: you do not own this record"));
            }
        }

        Map<String, Object> report = aiServiceClient.generateReport(record.getRawInput());
        if (report == null) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                    .body(Map.of("error", "AI service temporarily unavailable"));
        }
        return ResponseEntity.ok(report);
    }

    /**
     * GET /api/records/export — CSV export of all records.
     * ADMIN ONLY: enforced server-side.
     */
    @GetMapping("/export")
    public ResponseEntity<?> exportToCSV(Authentication authentication) {
        // Backend authorization enforcement — not just a UI hint
        if (!isAdmin(authentication)) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN)
                    .body(Map.of("error", "Access denied: admin role required for CSV export"));
        }

        List<ComplianceRecord> records = complianceService.getAllRecords();
        StringBuilder csv = new StringBuilder("ID,Status,Submitted By,Raw Input,DPO Summary\n");

        for (ComplianceRecord record : records) {
            String cleanInput = record.getRawInput() != null
                    ? record.getRawInput().replace("\"", "\"\"") : "";
            String cleanSummary = record.getProfessionalDescription() != null
                    ? record.getProfessionalDescription().replace("\"", "\"\"") : "";
            String submittedBy = record.getSubmittedBy() != null
                    ? record.getSubmittedBy() : "system";

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
package com.campuspe.dpdp.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import com.campuspe.dpdp.model.ComplianceRecord;
import com.campuspe.dpdp.repository.ComplianceRepository;

/**
 * Separate Spring bean for the @Async AI enrichment task.
 *
 * WHY THIS EXISTS:
 * Spring's @Async works by wrapping the bean in a proxy. If enrichRecordWithAi()
 * was called from within ComplianceService (self-invocation), Spring's proxy is
 * bypassed and @Async has no effect — the call runs synchronously on the same
 * thread, blocking the HTTP response.
 *
 * By placing the async method in a *separate* bean (AsyncEnricher) and injecting
 * it into ComplianceService, the call goes through the Spring proxy and runs in
 * the configured async thread pool.
 */
@Service
public class AsyncEnricher {

    @Autowired
    private ComplianceRepository repository;

    @Autowired
    private AiServiceClient aiServiceClient;

    /**
     * Called after a record is saved. Runs in a background thread.
     * Updates the record with the AI-generated professional description.
     */
    @Async
    public void enrichRecordWithAi(Long recordId, String rawInput) {
        try {
            String cleanDescription = aiServiceClient.getProfessionalDescription(rawInput);

            ComplianceRecord record = repository.findById(recordId).orElse(null);
            if (record != null) {
                record.setProfessionalDescription(
                        cleanDescription != null ? cleanDescription : "AI processing failed. Pending manual review."
                );
                record.setStatus("COMPLETED");
                repository.save(record);
            }
        } catch (Exception e) {
            System.err.println("[AsyncEnricher] Failed to enrich record " + recordId + ": " + e.getMessage());
            // Mark as failed so the UI does not show PROCESSING forever
            repository.findById(recordId).ifPresent(record -> {
                record.setStatus("FAILED");
                repository.save(record);
            });
        }
    }
}

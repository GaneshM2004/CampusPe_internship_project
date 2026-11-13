package com.campuspe.dpdp.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.campuspe.dpdp.model.ComplianceRecord;
import com.campuspe.dpdp.model.User;
import com.campuspe.dpdp.repository.ComplianceRepository;

import java.util.List;

@Service
public class ComplianceService {

    @Autowired
    private ComplianceRepository repository;

    @Autowired
    private AiServiceClient aiServiceClient;

    /**
     * AsyncEnricher is a separate bean so that the @Async proxy is NOT bypassed.
     * See AsyncEnricher.java for the explanation of the self-invocation problem.
     */
    @Autowired
    private AsyncEnricher asyncEnricher;

    /**
     * Create a new compliance record, attaching the authenticated user.
     * The record is immediately saved with status=PROCESSING.
     * AI enrichment runs asynchronously via AsyncEnricher.
     */
    public ComplianceRecord createRecord(String rawInput, User user) {
        ComplianceRecord record = new ComplianceRecord();
        record.setRawInput(rawInput);
        record.setStatus("PROCESSING");
        record.setUser(user);

        // Save the raw record immediately so the UI can show it
        ComplianceRecord savedRecord = repository.save(record);

        // Fire the AI enrichment in a background thread (through Spring proxy)
        asyncEnricher.enrichRecordWithAi(savedRecord.getId(), rawInput);

        return savedRecord;
    }

    /**
     * ADMIN: return all records.
     */
    public List<ComplianceRecord> getAllRecords() {
        return repository.findAll();
    }

    /**
     * USER: return only records belonging to this user.
     */
    public List<ComplianceRecord> getRecordsByUserId(Long userId) {
        return repository.findByUserId(userId);
    }

    /**
     * Fetch a single record by its ID.
     */
    public ComplianceRecord getRecordById(Long id) {
        return repository.findById(id).orElse(null);
    }
}
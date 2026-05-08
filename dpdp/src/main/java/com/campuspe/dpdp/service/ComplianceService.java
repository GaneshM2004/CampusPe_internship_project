package com.campuspe.dpdp.service;

import org.springframework.stereotype.Service;
import org.springframework.scheduling.annotation.Async;
import org.springframework.beans.factory.annotation.Autowired;

import com.campuspe.dpdp.model.ComplianceRecord;
import com.campuspe.dpdp.repository.ComplianceRepository;

@Service
public class ComplianceService {

    @Autowired
    private ComplianceRepository repository;

    @Autowired
    private AiServiceClient aiServiceClient;

    // The method the frontend calls immediately
    public ComplianceRecord createRecord(String rawInput) {
        ComplianceRecord record = new ComplianceRecord();
        record.setRawInput(rawInput);
        record.setStatus("PROCESSING");
        
        // Save the raw record immediately
        ComplianceRecord savedRecord = repository.save(record);
        
        // Fire off the AI task in the background (Day 7 Task!)
        enrichRecordWithAi(savedRecord.getId(), rawInput);
        
        return savedRecord;
    }

    // Day 7 @Async Task
    @Async
    public void enrichRecordWithAi(Long recordId, String rawInput) {
        try {
            // 1. Call your Flask Python server
            String cleanDescription = aiServiceClient.getProfessionalDescription(rawInput);
            
            // 2. Fetch the record from DB
            ComplianceRecord record = repository.findById(recordId).orElse(null);
            
            if (record != null) {
                // 3. Attach AI result and update status (handle nulls gracefully)
                record.setProfessionalDescription(cleanDescription);
                record.setStatus("COMPLETED");
                repository.save(record);
            }
        } catch (Exception e) {
            System.err.println("Failed to enrich record " + recordId);
        }
    }
    public java.util.List<ComplianceRecord> getAllRecords() {
        return repository.findAll();
    }
    // Fetch a single record by its ID
    public ComplianceRecord getRecordById(Long id) {
        return repository.findById(id).orElse(null);
    }

}
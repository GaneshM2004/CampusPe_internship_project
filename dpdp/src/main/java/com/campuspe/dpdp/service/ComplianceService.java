package com.campuspe.dpdp.service;

import org.springframework.stereotype.Service;
import org.springframework.scheduling.annotation.Async;
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
     * Create a new compliance record, attaching the authenticated user.
     */
    public ComplianceRecord createRecord(String rawInput, User user) {
        ComplianceRecord record = new ComplianceRecord();
        record.setRawInput(rawInput);
        record.setStatus("PROCESSING");
        record.setUser(user);
        
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

    // Fetch a single record by its ID
    public ComplianceRecord getRecordById(Long id) {
        return repository.findById(id).orElse(null);
    }

}
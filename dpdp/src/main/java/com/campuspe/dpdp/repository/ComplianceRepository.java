package com.campuspe.dpdp.repository;

import com.campuspe.dpdp.model.ComplianceRecord;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ComplianceRepository extends JpaRepository<ComplianceRecord, Long> {

    /**
     * Returns all records created by a specific user (for USER-role scoping).
     */
    List<ComplianceRecord> findByUserId(Long userId);
}
package com.campuspe.dpdp.repository;

import com.campuspe.dpdp.model.ComplianceRecord;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ComplianceRepository extends JpaRepository<ComplianceRecord, Long> {
}
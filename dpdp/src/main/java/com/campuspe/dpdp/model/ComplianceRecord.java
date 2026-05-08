package com.campuspe.dpdp.model;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Lob;

@Entity
public class ComplianceRecord {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Lob
    private String rawInput;
    
    @Lob
    private String professionalDescription;
    
    private String status;

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    
    public String getRawInput() { return rawInput; }
    public void setRawInput(String rawInput) { this.rawInput = rawInput; }
    
    public String getProfessionalDescription() { return professionalDescription; }
    public void setProfessionalDescription(String professionalDescription) { this.professionalDescription = professionalDescription; }
    
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}

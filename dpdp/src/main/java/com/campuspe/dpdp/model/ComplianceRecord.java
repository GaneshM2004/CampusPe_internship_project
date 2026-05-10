package com.campuspe.dpdp.model;

import jakarta.persistence.*;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

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

    /**
     * The user who created this compliance record.
     * Nullable for backward-compatibility with seeded/legacy data.
     */
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "user_id")
    @JsonIgnoreProperties({"password"})
    private User user;

    // ── Getters and Setters ───────────────────────────────
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    
    public String getRawInput() { return rawInput; }
    public void setRawInput(String rawInput) { this.rawInput = rawInput; }
    
    public String getProfessionalDescription() { return professionalDescription; }
    public void setProfessionalDescription(String professionalDescription) { this.professionalDescription = professionalDescription; }
    
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public User getUser() { return user; }
    public void setUser(User user) { this.user = user; }

    /**
     * Convenience getter for the username of the record creator.
     * Returns null if no user is attached (legacy records).
     */
    public String getSubmittedBy() {
        return user != null ? user.getUsername() : null;
    }
}

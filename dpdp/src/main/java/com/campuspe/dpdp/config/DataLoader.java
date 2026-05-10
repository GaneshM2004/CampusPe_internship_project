package com.campuspe.dpdp.config;

import com.campuspe.dpdp.model.ComplianceRecord;
import com.campuspe.dpdp.model.Role;
import com.campuspe.dpdp.model.User;
import com.campuspe.dpdp.repository.ComplianceRepository;
import com.campuspe.dpdp.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Component
public class DataLoader implements CommandLineRunner {

    @Autowired
    private ComplianceRepository repository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Override
    public void run(String... args) throws Exception {

        // 1. Ensure the Admin user exists first
        User adminUser = userRepository.findByUsername("admin")
                .orElseGet(() -> {
                    User newAdmin = new User();
                    newAdmin.setUsername("admin");
                    newAdmin.setPassword(passwordEncoder.encode("admin_password"));
                    newAdmin.setRole(Role.ADMIN);
                    return userRepository.save(newAdmin);
                });
        System.out.println("✅ Admin account ensured");

        // Clean up legacy records with no user (since we use persistent file H2)
        List<ComplianceRecord> allRecords = repository.findAll();
        boolean hasLegacy = false;
        for(ComplianceRecord r : allRecords) {
            if(r.getUser() == null) {
                repository.delete(r);
                hasLegacy = true;
            }
        }
        if (hasLegacy) {
            System.out.println("🧹 Cleaned up legacy dummy records with no user attached.");
        }

        // 2. When creating your 30 dummy records, attach the admin user!
        if (repository.count() == 0) {
            System.out.println("Initializing Database with 30 Demo Records...");
            List<ComplianceRecord> records = new ArrayList<>();

            String[] sampleInputs = {
                "Marketing team wants to export customer emails to a third-party analytics tool.",
                "HR is moving employee payroll data to a new unverified cloud vendor.",
                "A developer accidentally committed a database password to a public GitHub repo.",
                "Customer support wants to record all phone calls for quality assurance.",
                "We received a Data Subject Access Request (DSAR) from a user in Europe."
            };

            String[] sampleSummaries = {
                "This action requires explicit user consent and a Data Processing Agreement (DPA) with the third-party tool under the DPDP Act.",
                "High Risk. Verify the cloud vendor's security certifications (ISO 27001) and ensure data localization requirements are met.",
                "Critical Security Incident. Immediately revoke the password, rotate credentials, and notify the Data Protection Officer.",
                "Consent must be obtained at the beginning of the call. Data retention policies must be strictly enforced.",
                "Must respond within the statutory timeframe. Ensure all personal data tied to the user can be securely extracted and provided."
            };

            for (int i = 1; i <= 30; i++) {
                ComplianceRecord record = new ComplianceRecord();
                // Pick a random scenario from our arrays
                int randomIndex = (int) (Math.random() * sampleInputs.length);
                
                record.setRawInput(sampleInputs[randomIndex] + " (Case ID: " + i + ")");
                
                // THIS IS THE MISSING MAGIC LINE:
                record.setUser(adminUser); 
                
                // Make 80% of them "COMPLETED" and 20% "PROCESSING" for a realistic dashboard
                if (Math.random() > 0.2) {
                    record.setStatus("COMPLETED");
                    record.setProfessionalDescription(sampleSummaries[randomIndex]);
                } else {
                    record.setStatus("PROCESSING");
                }
                
                records.add(record);
            }

            repository.saveAll(records);
            System.out.println("Successfully seeded 30 records!");
        }
    }
}
package com.campuspe.dpdp.config;

import com.campuspe.dpdp.model.ComplianceRecord;
import com.campuspe.dpdp.repository.ComplianceRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Component
public class DataLoader implements CommandLineRunner {

    @Autowired
    private ComplianceRepository repository;

    @Override
    public void run(String... args) throws Exception {
        // Only run the seeder if the database is completely empty
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

            for (int i = 0; i < 30; i++) {
                ComplianceRecord record = new ComplianceRecord();
                // Pick a random scenario from our arrays
                int randomIndex = (int) (Math.random() * sampleInputs.length);
                
                record.setRawInput(sampleInputs[randomIndex] + " (Case ID: " + i + ")");
                
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
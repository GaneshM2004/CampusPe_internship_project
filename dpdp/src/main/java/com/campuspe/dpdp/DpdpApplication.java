package com.campuspe.dpdp;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync; // Import this

@SpringBootApplication
@EnableAsync // Add this line!
public class DpdpApplication {
    public static void main(String[] args) {
        SpringApplication.run(DpdpApplication.class, args);
    }
}
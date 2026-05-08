package com.campuspe.dpdp.service;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.ResponseEntity;
import java.util.Map;
import java.util.HashMap;

@Service
public class AiServiceClient {

    private final RestTemplate restTemplate = new RestTemplate();
    private final String AI_SERVICE_URL = "http://localhost:5000";

    public String getProfessionalDescription(String rawInput) {
        try {
            String url = AI_SERVICE_URL + "/describe";
            Map<String, String> request = new HashMap<>();
            request.put("input_text", rawInput);

            ResponseEntity<Map> response = restTemplate.postForEntity(url, request, Map.class);
            
            if (response.getBody() != null) {
                return (String) response.getBody().get("professional_description");
            }
        } catch (Exception e) {
            System.err.println("AI Service Error: " + e.getMessage());
        }
        return "AI Processing Failed. Pending manual review.";
    }
    // 1. Fetch 3 Actionable Recommendations
    public java.util.List<Map<String, String>> getRecommendations(String rawInput) {
        try {
            String url = AI_SERVICE_URL + "/recommend";
            Map<String, String> request = new HashMap<>();
            request.put("input_text", rawInput);

            ResponseEntity<Map> response = restTemplate.postForEntity(url, request, Map.class);
            if (response.getBody() != null && response.getBody().containsKey("recommendations")) {
                return (java.util.List<Map<String, String>>) response.getBody().get("recommendations");
            }
        } catch (Exception e) {
            System.err.println("AI Recommend Error: " + e.getMessage());
        }
        return null;
    }

    // 2. Fetch the Full JSON Audit Report
    public Map<String, Object> generateReport(String rawInput) {
        try {
            String url = AI_SERVICE_URL + "/generate-report";
            Map<String, String> request = new HashMap<>();
            request.put("input_text", rawInput);

            ResponseEntity<Map> response = restTemplate.postForEntity(url, request, Map.class);
            if (response.getBody() != null) {
                return response.getBody();
            }
        } catch (Exception e) {
            System.err.println("AI Report Error: " + e.getMessage());
        }
        return null;
    }
}
package com.campuspe.dpdp.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * HTTP client for the Flask AI microservice.
 *
 * URL is configured via the ai.service.url property (application.properties),
 * which defaults to http://localhost:5000 locally and http://ai-service:5000
 * inside Docker Compose (set via AI_SERVICE_URL env var).
 */
@Service
public class AiServiceClient {

    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${ai.service.url:http://localhost:5000}")
    private String aiServiceUrl;

    /**
     * POST /describe — returns a professional DPO description.
     * Returns a fallback message if the AI service is unreachable.
     */
    public String getProfessionalDescription(String rawInput) {
        try {
            String url = aiServiceUrl + "/describe";
            Map<String, String> request = new HashMap<>();
            request.put("input_text", rawInput);

            ResponseEntity<Map> response = restTemplate.postForEntity(url, request, Map.class);
            if (response.getBody() != null && response.getBody().containsKey("professional_description")) {
                return (String) response.getBody().get("professional_description");
            }
        } catch (ResourceAccessException e) {
            System.err.println("[AiServiceClient] AI service unreachable: " + e.getMessage());
        } catch (RestClientException e) {
            System.err.println("[AiServiceClient] AI service error: " + e.getMessage());
        } catch (Exception e) {
            System.err.println("[AiServiceClient] Unexpected error: " + e.getMessage());
        }
        return null;  // caller should handle null gracefully
    }

    /**
     * POST /recommend — returns 3 actionable compliance recommendations.
     * Returns null if the AI service is unreachable.
     */
    public List<Map<String, String>> getRecommendations(String rawInput) {
        try {
            String url = aiServiceUrl + "/recommend";
            Map<String, String> request = new HashMap<>();
            request.put("input_text", rawInput);

            ResponseEntity<Map> response = restTemplate.postForEntity(url, request, Map.class);
            if (response.getBody() != null && response.getBody().containsKey("recommendations")) {
                return (List<Map<String, String>>) response.getBody().get("recommendations");
            }
        } catch (ResourceAccessException e) {
            System.err.println("[AiServiceClient] AI service unreachable: " + e.getMessage());
        } catch (RestClientException e) {
            System.err.println("[AiServiceClient] AI service error: " + e.getMessage());
        } catch (Exception e) {
            System.err.println("[AiServiceClient] Unexpected error: " + e.getMessage());
        }
        return null;
    }

    /**
     * POST /generate-report — returns a full audit report as a map.
     * Returns null if the AI service is unreachable.
     */
    public Map<String, Object> generateReport(String rawInput) {
        try {
            String url = aiServiceUrl + "/generate-report";
            Map<String, String> request = new HashMap<>();
            request.put("input_text", rawInput);

            ResponseEntity<Map> response = restTemplate.postForEntity(url, request, Map.class);
            if (response.getBody() != null) {
                return response.getBody();
            }
        } catch (ResourceAccessException e) {
            System.err.println("[AiServiceClient] AI service unreachable: " + e.getMessage());
        } catch (RestClientException e) {
            System.err.println("[AiServiceClient] AI service error: " + e.getMessage());
        } catch (Exception e) {
            System.err.println("[AiServiceClient] Unexpected error: " + e.getMessage());
        }
        return null;
    }
}
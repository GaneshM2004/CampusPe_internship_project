package com.campuspe.dpdp.controller;

import com.campuspe.dpdp.model.ComplianceRecord;
import com.campuspe.dpdp.model.Role;
import com.campuspe.dpdp.model.User;
import com.campuspe.dpdp.repository.UserRepository;
import com.campuspe.dpdp.service.AiServiceClient;
import com.campuspe.dpdp.service.ComplianceService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.*;

class ComplianceControllerTest {

    @Mock
    private ComplianceService complianceService;

    @Mock
    private AiServiceClient aiServiceClient;

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private ComplianceController controller;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    private Authentication authFor(Long userId, String role) {
        UsernamePasswordAuthenticationToken auth = new UsernamePasswordAuthenticationToken(
                "user" + userId,
                null,
                List.of(new SimpleGrantedAuthority(role))
        );
        auth.setDetails(userId);
        return auth;
    }

    @Test
    void getRecordRecommendations_NonOwnerUser_ReturnsForbidden() {
        User owner = new User("owner", "hash", Role.USER);
        owner.setId(10L);
        ComplianceRecord record = new ComplianceRecord();
        record.setId(1L);
        record.setUser(owner);

        when(complianceService.getRecordById(1L)).thenReturn(record);

        Authentication otherUser = authFor(99L, "ROLE_USER");
        ResponseEntity<?> response = controller.getRecordRecommendations(1L, otherUser);

        assertEquals(HttpStatus.FORBIDDEN, response.getStatusCode());
        verifyNoInteractions(aiServiceClient);
    }

    @Test
    void exportToCSV_NonAdminUser_ReturnsForbidden() {
        Authentication regularUser = authFor(10L, "ROLE_USER");
        ResponseEntity<?> response = controller.exportToCSV(regularUser);

        assertEquals(HttpStatus.FORBIDDEN, response.getStatusCode());
        verifyNoInteractions(complianceService);
    }
}

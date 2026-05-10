package com.campuspe.dpdp.service;

import com.campuspe.dpdp.model.ComplianceRecord;
import com.campuspe.dpdp.model.Role;
import com.campuspe.dpdp.model.User;
import com.campuspe.dpdp.repository.ComplianceRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.util.Arrays;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class ComplianceServiceTest {

    @Mock
    private ComplianceRepository repository;

    @Mock
    private AiServiceClient aiServiceClient;

    @InjectMocks
    private ComplianceService service;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    void createRecord_Success() {
        User testUser = new User("testuser", "hashed", Role.USER);
        ComplianceRecord record = new ComplianceRecord();
        record.setRawInput("Test data leak");
        record.setUser(testUser);
        when(repository.save(any())).thenReturn(record);

        ComplianceRecord saved = service.createRecord("Test data leak", testUser);
        assertNotNull(saved);
    }

    @Test
    void getAllRecords_ReturnsList() {
        when(repository.findAll()).thenReturn(Arrays.asList(new ComplianceRecord(), new ComplianceRecord()));
        List<ComplianceRecord> list = service.getAllRecords();
        assertEquals(2, list.size());
    }

    @Test
    void getRecordById_Found() {
        ComplianceRecord record = new ComplianceRecord();
        when(repository.findById(1L)).thenReturn(Optional.of(record));
        assertNotNull(service.getRecordById(1L));
    }

    @Test
    void getRecordById_NotFound() {
        when(repository.findById(99L)).thenReturn(Optional.empty());
        assertNull(service.getRecordById(99L));
    }
}

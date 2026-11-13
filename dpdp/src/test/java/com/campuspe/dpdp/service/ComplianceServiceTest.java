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

    /**
     * AsyncEnricher is mocked here because ComplianceService now delegates
     * the @Async enrichment to this separate bean (fixing the self-invocation problem).
     */
    @Mock
    private AsyncEnricher asyncEnricher;

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

        // The first save (immediate) returns the record
        when(repository.save(any())).thenReturn(record);
        // AsyncEnricher.enrichRecordWithAi is mocked — no actual async call in tests
        doNothing().when(asyncEnricher).enrichRecordWithAi(any(), any());

        ComplianceRecord saved = service.createRecord("Test data leak", testUser);
        assertNotNull(saved);
        // Verify that async enrichment was triggered
        verify(asyncEnricher, times(1)).enrichRecordWithAi(any(), eq("Test data leak"));
    }

    @Test
    void createRecord_AsyncEnricherIsCalled() {
        User testUser = new User("testuser", "hashed", Role.USER);
        ComplianceRecord record = new ComplianceRecord();
        record.setRawInput("Cloud data processing incident");
        record.setUser(testUser);

        when(repository.save(any())).thenReturn(record);
        doNothing().when(asyncEnricher).enrichRecordWithAi(any(), any());

        service.createRecord("Cloud data processing incident", testUser);

        // The async enricher must be called once per record creation
        verify(asyncEnricher, times(1)).enrichRecordWithAi(any(), anyString());
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

    @Test
    void getRecordsByUserId_ReturnsUserRecords() {
        ComplianceRecord r1 = new ComplianceRecord();
        when(repository.findByUserId(42L)).thenReturn(List.of(r1));
        List<ComplianceRecord> results = service.getRecordsByUserId(42L);
        assertEquals(1, results.size());
    }
}

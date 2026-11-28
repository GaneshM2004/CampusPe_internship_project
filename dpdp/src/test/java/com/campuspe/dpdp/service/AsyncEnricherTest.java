package com.campuspe.dpdp.service;

import com.campuspe.dpdp.model.ComplianceRecord;
import com.campuspe.dpdp.repository.ComplianceRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.*;

class AsyncEnricherTest {

    @Mock
    private ComplianceRepository repository;

    @Mock
    private AiServiceClient aiServiceClient;

    @InjectMocks
    private AsyncEnricher asyncEnricher;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    void enrichRecordWithAi_Success_TransitionsToCompleted() {
        ComplianceRecord record = new ComplianceRecord();
        record.setId(1L);
        record.setStatus("PROCESSING");

        when(aiServiceClient.getProfessionalDescription("raw text")).thenReturn("Enriched DPO description.");
        when(repository.findById(1L)).thenReturn(Optional.of(record));

        asyncEnricher.enrichRecordWithAi(1L, "raw text");

        assertEquals("COMPLETED", record.getStatus());
        assertEquals("Enriched DPO description.", record.getProfessionalDescription());
        verify(repository, times(1)).save(record);
    }

    @Test
    void enrichRecordWithAi_AiThrowsException_TransitionsToFailed() {
        ComplianceRecord record = new ComplianceRecord();
        record.setId(2L);
        record.setStatus("PROCESSING");

        when(aiServiceClient.getProfessionalDescription("raw text")).thenThrow(new RuntimeException("AI timeout"));
        when(repository.findById(2L)).thenReturn(Optional.of(record));

        asyncEnricher.enrichRecordWithAi(2L, "raw text");

        assertEquals("FAILED", record.getStatus());
        verify(repository, times(1)).save(record);
    }
}

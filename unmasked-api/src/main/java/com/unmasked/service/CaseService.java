package com.unmasked.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.unmasked.model.Case;
import com.unmasked.repository.CaseRepository;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;

import java.math.BigDecimal;
import java.util.Map;
import java.util.UUID;

@Service
public class CaseService {

    private final CaseRepository caseRepository;
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    private static final String INVESTIGATION_QUEUE = "unmasked:investigation_queue";

    public CaseService(CaseRepository caseRepository,
                       StringRedisTemplate redisTemplate,
                       ObjectMapper objectMapper) {
        this.caseRepository = caseRepository;
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
    }

    public Case createCase(String victimVpa, String fraudVpa,
                           BigDecimal amount, String transactionRef) {
        Case newCase = new Case();
        newCase.setVictimVpa(victimVpa);
        newCase.setFraudVpa(fraudVpa);
        newCase.setAmount(amount);
        newCase.setTransactionRef(transactionRef);
        newCase.setStatus("queued");

        // high priority if amount > 1 lakh
        if (amount.compareTo(new BigDecimal("100000")) > 0) {
            newCase.setPriority(1);
        }

        Case saved = caseRepository.save(newCase);

        // dispatch job to Redis queue for Python Celery worker to consume
        try {
            Map<String, Object> job = Map.of(
                "case_id", saved.getCaseId().toString(),
                "victim_vpa", victimVpa,
                "fraud_vpa", fraudVpa,
                "amount", amount.toString(),
                "transaction_ref", transactionRef
            );
            redisTemplate.opsForList().leftPush(
                INVESTIGATION_QUEUE,
                objectMapper.writeValueAsString(job)
            );
        } catch (Exception e) {
            saved.setStatus("failed");
            caseRepository.save(saved);
            throw new RuntimeException("Failed to dispatch investigation job", e);
        }

        return saved;
    }

    public Case getCase(UUID caseId) {
        return caseRepository.findById(caseId)
                .orElseThrow(() -> new RuntimeException("Case not found: " + caseId));
    }

    public Page<Case> getAllCases(int page, int size) {
        return caseRepository.findAll(
            PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"))
        );
    }
}

package com.unmasked.controller;

import com.unmasked.dto.CreateCaseRequest;
import com.unmasked.model.Case;
import com.unmasked.model.CaseReport;
import com.unmasked.repository.CaseReportRepository;
import com.unmasked.service.CaseService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/cases")
@CrossOrigin(origins = "*")
public class CaseController {

    private final CaseService caseService;
    private final CaseReportRepository reportRepository;

    public CaseController(CaseService caseService, CaseReportRepository reportRepository) {
        this.caseService = caseService;
        this.reportRepository = reportRepository;
    }

    // POST /api/cases — submit a new fraud case for investigation
    @PostMapping
    public ResponseEntity<?> createCase(@Valid @RequestBody CreateCaseRequest request) {
        Case created = caseService.createCase(
            request.getVictimVpa(),
            request.getFraudVpa(),
            request.getAmount(),
            request.getTransactionRef()
        );
        return ResponseEntity.status(HttpStatus.CREATED).body(Map.of(
            "case_id", created.getCaseId(),
            "status", created.getStatus(),
            "message", "Investigation queued"
        ));
    }

    // GET /api/cases/{id} — poll case status
    @GetMapping("/{id}")
    public ResponseEntity<?> getCase(@PathVariable UUID id) {
        Case c = caseService.getCase(id);
        return ResponseEntity.ok(Map.of(
            "case_id", c.getCaseId(),
            "status", c.getStatus(),
            "fraud_vpa", c.getFraudVpa(),
            "amount", c.getAmount(),
            "created_at", c.getCreatedAt().toString()
        ));
    }

    // GET /api/cases/{id}/report — fetch completed investigation report
    @GetMapping("/{id}/report")
    public ResponseEntity<?> getReport(@PathVariable UUID id) {
        // verify case exists
        caseService.getCase(id);

        CaseReport report = reportRepository.findById(id).orElse(null);
        if (report == null) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(Map.of("error", "Report not yet generated", "case_id", id));
        }
        return ResponseEntity.ok(report);
    }

    // GET /api/cases — list recent cases
    @GetMapping
    public ResponseEntity<?> listCases(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        var cases = caseService.getAllCases(page, size);
        return ResponseEntity.ok(cases);
    }
}

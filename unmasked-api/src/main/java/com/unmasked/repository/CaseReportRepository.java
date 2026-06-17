package com.unmasked.repository;

import com.unmasked.model.CaseReport;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;

public interface CaseReportRepository extends JpaRepository<CaseReport, UUID> {
}
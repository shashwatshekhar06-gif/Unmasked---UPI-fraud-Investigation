package com.unmasked.repository;

import com.unmasked.model.Case;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;

public interface CaseRepository extends JpaRepository<Case, UUID> {
}
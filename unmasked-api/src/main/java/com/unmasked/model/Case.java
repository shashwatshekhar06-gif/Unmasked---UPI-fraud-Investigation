package com.unmasked.model;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "cases")
public class Case {

    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    @Column(name = "case_id")
    private UUID caseId;

    @Column(name = "victim_vpa", nullable = false)
    private String victimVpa;

    @Column(name = "fraud_vpa", nullable = false)
    private String fraudVpa;

    @Column(nullable = false)
    private BigDecimal amount;

    @Column(name = "transaction_ref", nullable = false, unique = true)
    private String transactionRef;

    @Column(nullable = false)
    private String status = "queued";

    @Column(name = "created_at")
    private OffsetDateTime createdAt = OffsetDateTime.now();

    @Column(name = "completed_at")
    private OffsetDateTime completedAt;

    @Column(name = "source_channel")
    private String sourceChannel = "web";

    private Integer priority = 0;

    // Getters and setters
    public UUID getCaseId() { return caseId; }
    public void setCaseId(UUID caseId) { this.caseId = caseId; }

    public String getVictimVpa() { return victimVpa; }
    public void setVictimVpa(String victimVpa) { this.victimVpa = victimVpa; }

    public String getFraudVpa() { return fraudVpa; }
    public void setFraudVpa(String fraudVpa) { this.fraudVpa = fraudVpa; }

    public BigDecimal getAmount() { return amount; }
    public void setAmount(BigDecimal amount) { this.amount = amount; }

    public String getTransactionRef() { return transactionRef; }
    public void setTransactionRef(String transactionRef) { this.transactionRef = transactionRef; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }

    public OffsetDateTime getCompletedAt() { return completedAt; }
    public void setCompletedAt(OffsetDateTime completedAt) { this.completedAt = completedAt; }

    public String getSourceChannel() { return sourceChannel; }
    public void setSourceChannel(String sourceChannel) { this.sourceChannel = sourceChannel; }

    public Integer getPriority() { return priority; }
    public void setPriority(Integer priority) { this.priority = priority; }
}

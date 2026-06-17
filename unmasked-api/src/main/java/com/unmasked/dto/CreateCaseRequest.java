package com.unmasked.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;

public class CreateCaseRequest {

    @NotBlank(message = "Victim VPA is required")
    private String victimVpa;

    @NotBlank(message = "Fraud VPA is required")
    private String fraudVpa;

    @NotNull(message = "Amount is required")
    @DecimalMin(value = "0.01", message = "Amount must be positive")
    private BigDecimal amount;

    @NotBlank(message = "Transaction reference is required")
    private String transactionRef;

    public String getVictimVpa() { return victimVpa; }
    public void setVictimVpa(String victimVpa) { this.victimVpa = victimVpa; }
    public String getFraudVpa() { return fraudVpa; }
    public void setFraudVpa(String fraudVpa) { this.fraudVpa = fraudVpa; }
    public BigDecimal getAmount() { return amount; }
    public void setAmount(BigDecimal amount) { this.amount = amount; }
    public String getTransactionRef() { return transactionRef; }
    public void setTransactionRef(String transactionRef) { this.transactionRef = transactionRef; }
}
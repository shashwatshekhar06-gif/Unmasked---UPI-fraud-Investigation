package com.unmasked.model;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "case_reports")
public class CaseReport {

    @Id
    @Column(name = "case_id")
    private UUID caseId;

    @Column(name = "report_markdown", columnDefinition = "TEXT")
    private String reportMarkdown;

    @Column(name = "confidence_overall")
    private BigDecimal confidenceOverall;

    @Column(name = "scam_pattern")
    private String scamPattern;

    @Column(name = "matched_advisory")
    private String matchedAdvisory;

    @Column(name = "network_size")
    private Integer networkSize;

    @Column(name = "trail_status")
    private String trailStatus;

    @Column(name = "graph_json", columnDefinition = "jsonb")
    private String graphJson;

    @Column(name = "generated_at")
    private OffsetDateTime generatedAt = OffsetDateTime.now();

    public UUID getCaseId() { return caseId; }
    public void setCaseId(UUID caseId) { this.caseId = caseId; }

    public String getReportMarkdown() { return reportMarkdown; }
    public void setReportMarkdown(String reportMarkdown) { this.reportMarkdown = reportMarkdown; }

    public BigDecimal getConfidenceOverall() { return confidenceOverall; }
    public void setConfidenceOverall(BigDecimal confidenceOverall) { this.confidenceOverall = confidenceOverall; }

    public String getScamPattern() { return scamPattern; }
    public void setScamPattern(String scamPattern) { this.scamPattern = scamPattern; }

    public String getMatchedAdvisory() { return matchedAdvisory; }
    public void setMatchedAdvisory(String matchedAdvisory) { this.matchedAdvisory = matchedAdvisory; }

    public Integer getNetworkSize() { return networkSize; }
    public void setNetworkSize(Integer networkSize) { this.networkSize = networkSize; }

    public String getTrailStatus() { return trailStatus; }
    public void setTrailStatus(String trailStatus) { this.trailStatus = trailStatus; }

    public String getGraphJson() { return graphJson; }
    public void setGraphJson(String graphJson) { this.graphJson = graphJson; }

    public OffsetDateTime getGeneratedAt() { return generatedAt; }
    public void setGeneratedAt(OffsetDateTime generatedAt) { this.generatedAt = generatedAt; }
}

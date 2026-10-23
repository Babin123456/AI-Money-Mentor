/**
 * Loan Planner & Debt Payoff Strategy Optimizer
 * Handles interactive EMI calculations, accelerated prepayment simulations,
 * and Avalanche vs. Snowball payoff strategy comparisons.
 */

let loanChart = null;
let accelerationChart = null;

async function calcLoan() {
  const principal_front = document.getElementById("principal").value;
  const rate_front = document.getElementById("rate").value;
  const time_front = document.getElementById("time").value;
  const income_front = document.getElementById("income").value;

  if (!principal_front || !rate_front || !time_front || !income_front) {
    showLoanMsg("Msg", "Please fill in all loan details.", "warning");
    return;
  }

  setBtnLoading("Btn", true);
  showLoanMsg("Msg", "Calculating loan metrics...", "info");

  try {
    const response = await fetch("/loan_info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        principal: parseFloat(principal_front),
        rate: parseFloat(rate_front),
        time: parseFloat(time_front),
        income: parseFloat(income_front)
      })
    });

    const data = await response.json();
    if (!response.ok || data.error) {
      showLoanMsg("Msg", data.error || "Failed to calculate loan.", "error");
      setBtnLoading("Btn", false);
      return;
    }

    showLoanMsg("Msg", "Calculation completed successfully!", "success");

    // Populate Baseline summary
    document.getElementById("LoanEmicalc").innerHTML = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 6px;">
        <p style="margin: 4px 0;"><strong>Total Loan:</strong> ₹${Number(data.Loan_Amount).toLocaleString()}</p>
        <p style="margin: 4px 0;"><strong>Total Interest:</strong> ₹${Number(data.Loan_Interest).toLocaleString()}</p>
        <p style="margin: 4px 0;"><strong>Monthly EMI:</strong> ₹${Number(data.EMI).toLocaleString()}</p>
        <p style="margin: 4px 0;"><strong>Net Take-Home:</strong> ₹${Number(data.Net_take_income).toLocaleString()}</p>
      </div>
    `;

    // Reliability & Zone verdict
    let zoneClass = "badge-safe";
    let zoneLabel = "Safe Choice";
    if (data.Zone === 0) {
      zoneClass = "badge-moderate";
      zoneLabel = "Moderate (Refinance Advice Recommended)";
    } else if (data.Zone === -1) {
      zoneClass = "badge-danger";
      zoneLabel = "High Risk (EMI > 45% of Income)";
    }

    document.getElementById("Reliability").innerHTML = `
      <p style="margin: 4px 0;"><strong>Debt-to-Income Ratio:</strong> ${(data.Ratio * 100).toFixed(1)}%</p>
      <p style="margin: 4px 0;"><strong>Risk Verdict:</strong> <span class="custom-badge ${zoneClass}">${zoneLabel}</span></p>
    `;

    // AI Prediction Advisory
    if (document.getElementById("aiPredictionResult")) {
      document.getElementById("aiPredictionResult").innerHTML = `
        <div style="color: var(--text-color, #e0e0e0); font-size: 13.5px; line-height: 1.5; white-space: pre-line;">
          ${data.Advice || "No specific risks flagged."}
        </div>
      `;
    }

    // Baseline chart
    renderBaselineChart(parseFloat(principal_front), parseFloat(rate_front), parseInt(time_front));

    // Also populate default values in Prepayment section if available
    const prepayPrincipal = document.getElementById("prepay-principal");
    if (prepayPrincipal && !prepayPrincipal.value) {
      prepayPrincipal.value = principal_front;
      document.getElementById("prepay-rate").value = rate_front;
      document.getElementById("prepay-time").value = time_front;
    }

  } catch (err) {
    console.error("Loan calculation error:", err);
    showLoanMsg("Msg", "Server connection error. Please try again.", "error");
  } finally {
    setBtnLoading("Btn", false);
  }
}

function renderBaselineChart(principal, ratePercent, years) {
  const chartCanvas = document.getElementById("Chart");
  if (!chartCanvas) return;

  const labels = [];
  const balances = [];
  const r = ratePercent / 100;

  for (let i = 1; i <= years; i++) {
    labels.push(`Year ${i}`);
    balances.push(Math.round(principal * Math.pow(1 + r, i)));
  }

  if (loanChart) loanChart.destroy();
  const ctx = chartCanvas.getContext("2d");
  loanChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Estimated Growth / Compounding Balance",
        data: balances,
        borderColor: "#d4af37",
        backgroundColor: "rgba(212, 175, 55, 0.1)",
        fill: true,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#ccc" } }
      },
      scales: {
        x: { ticks: { color: "#999" } },
        y: { ticks: { color: "#999" } }
      }
    }
  });
}

async function simulatePrepayment() {
  const principal = parseFloat(document.getElementById("prepay-principal").value || 0);
  const rate = parseFloat(document.getElementById("prepay-rate").value || 0);
  const time = parseFloat(document.getElementById("prepay-time").value || 0);
  const extraMonthly = parseFloat(document.getElementById("prepay-extra").value || 0);
  const lumpSum = parseFloat(document.getElementById("prepay-lump").value || 0);
  const lumpMonth = parseInt(document.getElementById("prepay-lump-month").value || 1);

  if (principal <= 0 || time <= 0) {
    alert("Please provide valid Principal and Tenure.");
    return;
  }

  const resultContainer = document.getElementById("prepay-results");
  if (resultContainer) {
    resultContainer.innerHTML = `<div style="text-align: center; padding: 20px; color: var(--gold);"><i class="fa-solid fa-spinner fa-spin"></i> Simulating prepayment impact...</div>`;
  }

  try {
    const res = await fetch("/api/loan/prepayment-simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        principal: principal,
        rate: rate,
        time: time,
        extra_monthly: extraMonthly,
        lump_sum: lumpSum,
        lump_sum_month: lumpMonth
      })
    });

    const data = await res.json();
    if (!res.ok || data.error) {
      if (resultContainer) resultContainer.innerHTML = `<p style="color: #e63946;">${data.error || "Simulation error."}</p>`;
      return;
    }

    const baseline = data.baseline;
    const accel = data.accelerated;

    resultContainer.innerHTML = `
      <div class="prepay-stats-grid">
        <div class="prepay-stat-card highlight-card">
          <div class="stat-title">Interest Saved</div>
          <div class="stat-value text-green">₹${Number(accel.interest_saved).toLocaleString()}</div>
          <div class="stat-sub">(${accel.interest_reduction_percent}% interest reduction)</div>
        </div>
        <div class="prepay-stat-card">
          <div class="stat-title">Tenure Reduced</div>
          <div class="stat-value text-gold">${accel.years_saved} Years</div>
          <div class="stat-sub">${accel.months_saved} months eliminated</div>
        </div>
        <div class="prepay-stat-card">
          <div class="stat-title">Total Accelerated Payment</div>
          <div class="stat-value">₹${Number(accel.total_payment).toLocaleString()}</div>
          <div class="stat-sub">vs ₹${Number(baseline.total_payment).toLocaleString()} original</div>
        </div>
        <div class="prepay-stat-card">
          <div class="stat-title">Payoff Duration</div>
          <div class="stat-value text-cyan">${accel.total_months} Months</div>
          <div class="stat-sub">Down from ${baseline.total_months} months</div>
        </div>
      </div>
    `;

  } catch (err) {
    console.error("Prepayment simulation error:", err);
    if (resultContainer) {
      resultContainer.innerHTML = `<p style="color: #e63946;">Failed to connect to simulation engine.</p>`;
    }
  }
}

// Sample debt list for Avalanche vs Snowball
let debtList = [
  { name: "Credit Card", balance: 50000, interest_rate: 36.0, min_payment: 2500 },
  { name: "Personal Loan", balance: 180000, interest_rate: 14.5, min_payment: 5500 },
  { name: "Auto Loan", balance: 350000, interest_rate: 9.0, min_payment: 8200 }
];

function renderDebtTable() {
  const tbody = document.getElementById("debt-list-body");
  if (!tbody) return;

  tbody.innerHTML = debtList.map((d, index) => `
    <tr>
      <td><strong>${d.name}</strong></td>
      <td>₹${Number(d.balance).toLocaleString()}</td>
      <td><span class="custom-badge badge-rate">${d.interest_rate}%</span></td>
      <td>₹${Number(d.min_payment).toLocaleString()}</td>
      <td><button class="btn btn-ghost btn-sm" onclick="removeDebt(${index})"><i class="fa-solid fa-trash"></i></button></td>
    </tr>
  `).join("");
}

function addDebt() {
  const name = document.getElementById("new-debt-name").value.trim();
  const balance = parseFloat(document.getElementById("new-debt-balance").value || 0);
  const rate = parseFloat(document.getElementById("new-debt-rate").value || 0);
  const minPay = parseFloat(document.getElementById("new-debt-min").value || 0);

  if (!name || balance <= 0 || rate <= 0 || minPay <= 0) {
    alert("Please fill in all debt fields with valid positive numbers.");
    return;
  }

  debtList.push({ name: name, balance: balance, interest_rate: rate, min_payment: minPay });
  document.getElementById("new-debt-name").value = "";
  document.getElementById("new-debt-balance").value = "";
  document.getElementById("new-debt-rate").value = "";
  document.getElementById("new-debt-min").value = "";

  renderDebtTable();
}

function removeDebt(index) {
  debtList.splice(index, 1);
  renderDebtTable();
}

async function comparePayoffStrategies() {
  if (debtList.length === 0) {
    alert("Please add at least one debt.");
    return;
  }

  const extraBudget = parseFloat(document.getElementById("extra-debt-budget").value || 0);
  const container = document.getElementById("strategy-results");
  if (container) {
    container.innerHTML = `<div style="text-align: center; padding: 20px; color: var(--gold);"><i class="fa-solid fa-spinner fa-spin"></i> Calculating payoff strategies...</div>`;
  }

  try {
    const res = await fetch("/api/loan/debt-payoff-compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        debts: debtList,
        extra_monthly_budget: extraBudget
      })
    });

    const data = await res.json();
    if (!res.ok || data.error) {
      if (container) container.innerHTML = `<p style="color: #e63946;">${data.error || "Strategy error."}</p>`;
      return;
    }

    const av = data.avalanche;
    const sn = data.snowball;

    container.innerHTML = `
      <div class="strategy-comparison-grid">
        <div class="strategy-card avalanche-card">
          <div class="card-badge badge-avalanche">Mathematically Optimal</div>
          <div class="strategy-title">🏔️ Debt Avalanche</div>
          <p class="strategy-desc">Prioritizes debts with the highest interest rate first.</p>
          <div class="strategy-metric">
            <span>Total Interest Paid:</span>
            <strong>₹${Number(av.total_interest_paid).toLocaleString()}</strong>
          </div>
          <div class="strategy-metric">
            <span>Debt-Free in:</span>
            <strong>${av.total_months} Months</strong>
          </div>
        </div>

        <div class="strategy-card snowball-card">
          <div class="card-badge badge-snowball">Psychological Momentum</div>
          <div class="strategy-title">⛄ Debt Snowball</div>
          <p class="strategy-desc">Prioritizes debts with the smallest balance first for quick wins.</p>
          <div class="strategy-metric">
            <span>Total Interest Paid:</span>
            <strong>₹${Number(sn.total_interest_paid).toLocaleString()}</strong>
          </div>
          <div class="strategy-metric">
            <span>Debt-Free in:</span>
            <strong>${sn.total_months} Months</strong>
          </div>
        </div>
      </div>

      <div class="strategy-recommendation-box">
        <i class="fa-solid fa-lightbulb" style="color: var(--gold); font-size: 18px;"></i>
        <div>
          <strong>AI Strategy Recommendation:</strong>
          <p style="margin: 4px 0 0 0; color: var(--text-color, #e0e0e0); font-size: 13.5px;">${data.recommendation}</p>
        </div>
      </div>
    `;

  } catch (err) {
    console.error("Strategy calculation error:", err);
    if (container) {
      container.innerHTML = `<p style="color: #e63946;">Failed to compare debt strategies.</p>`;
    }
  }
}

function resetLoan() {
  document.getElementById("principal").value = "";
  document.getElementById("rate").value = "";
  document.getElementById("time").value = "";
  document.getElementById("income").value = "";
  document.getElementById("LoanEmicalc").innerHTML = '<p style="color: var(--muted); font-size: 13px; margin: 0; padding-top: 4px;">Enter the info above to view the results</p>';
  document.getElementById("Reliability").innerHTML = '<p style="color: var(--muted); font-size: 13px; margin: 0; padding-top: 4px;">Enter the info above to view the results</p>';
  if (document.getElementById("aiPredictionResult")) {
    document.getElementById("aiPredictionResult").innerHTML = '<p style="color: var(--muted); font-size: 13px; margin: 0; padding-top: 4px;">Enter the info above to view the AI analysis.</p>';
  }
  if (loanChart) {
    loanChart.destroy();
    loanChart = null;
  }
}

function showLoanMsg(id, text, type) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = `result-box ${type}`;
}

function setBtnLoading(btnId, isLoading) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = isLoading;
  btn.innerHTML = isLoading ? '<i class="fa-solid fa-spinner fa-spin"></i> Processing...' : "Calculate";
}

document.addEventListener("DOMContentLoaded", () => {
  renderDebtTable();
});

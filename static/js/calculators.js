/**
 * PRIME RESERVE BANK - Real-time Interactive Financial Calculators
 * (EMI, FD, RD, SIP)
 */

document.addEventListener('DOMContentLoaded', function() {

    // ==========================================
    // 1. EMI CALCULATOR
    // ==========================================
    const emiAmountSlider = document.getElementById('emiAmountSlider');
    const emiAmountInput = document.getElementById('emiAmountInput');
    const emiRateSlider = document.getElementById('emiRateSlider');
    const emiRateInput = document.getElementById('emiRateInput');
    const emiTenureSlider = document.getElementById('emiTenureSlider');
    const emiTenureInput = document.getElementById('emiTenureInput');

    let emiChart = null;

    function calculateEMI() {
        if (!emiAmountSlider) return;
        const P = parseFloat(emiAmountInput.value) || 0;
        const annualRate = parseFloat(emiRateInput.value) || 0;
        const n = parseInt(emiTenureInput.value) || 0;

        if (P <= 0 || n <= 0) return;

        const r = (annualRate / 12.0) / 100.0;
        let emi = 0;
        if (r === 0) {
            emi = P / n;
        } else {
            emi = (P * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
        }

        const totalPayable = emi * n;
        const totalInterest = totalPayable - P;

        document.getElementById('emiMonthlyResult').innerText = '₹' + Math.round(emi).toLocaleString('en-IN');
        document.getElementById('emiTotalInterest').innerText = '₹' + Math.round(totalInterest).toLocaleString('en-IN');
        document.getElementById('emiTotalPayable').innerText = '₹' + Math.round(totalPayable).toLocaleString('en-IN');
        document.getElementById('emiPrincipalDisplay').innerText = '₹' + Math.round(P).toLocaleString('en-IN');

        const ctx = document.getElementById('emiChart');
        if (ctx) {
            if (emiChart) emiChart.destroy();
            emiChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Principal Amount', 'Total Interest'],
                    datasets: [{
                        data: [Math.round(P), Math.round(totalInterest)],
                        backgroundColor: ['#1a56db', '#f59e0b'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: { legend: { position: 'bottom' } }
                }
            });
        }
    }

    if (emiAmountSlider) {
        // Sync sliders and inputs
        function syncEmi(slider, input) {
            slider.addEventListener('input', () => { input.value = slider.value; calculateEMI(); });
            input.addEventListener('input', () => { slider.value = input.value; calculateEMI(); });
        }
        syncEmi(emiAmountSlider, emiAmountInput);
        syncEmi(emiRateSlider, emiRateInput);
        syncEmi(emiTenureSlider, emiTenureInput);
        calculateEMI();
    }


    // ==========================================
    // 2. FD CALCULATOR
    // ==========================================
    const fdPrincipalInput = document.getElementById('fdPrincipal');
    const fdRateInput = document.getElementById('fdRate');
    const fdTenureInput = document.getElementById('fdTenure');
    let fdChart = null;

    function calculateFD() {
        if (!fdPrincipalInput) return;
        const P = parseFloat(fdPrincipalInput.value) || 0;
        const rate = parseFloat(fdRateInput.value) || 0;
        const tenureMonths = parseInt(fdTenureInput.value) || 0;

        if (P <= 0 || tenureMonths <= 0) return;

        const r = rate / 100.0;
        const t = tenureMonths / 12.0;
        const n = 4; // Quarterly compounding
        const maturity = P * Math.pow(1 + (r / n), n * t);
        const interestEarned = maturity - P;

        document.getElementById('fdMaturityResult').innerText = '₹' + Math.round(maturity).toLocaleString('en-IN');
        document.getElementById('fdInterestResult').innerText = '₹' + Math.round(interestEarned).toLocaleString('en-IN');
        document.getElementById('fdInvestedResult').innerText = '₹' + Math.round(P).toLocaleString('en-IN');

        const ctx = document.getElementById('fdChart');
        if (ctx) {
            if (fdChart) fdChart.destroy();
            fdChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Invested Principal', 'Interest Earned'],
                    datasets: [{
                        data: [Math.round(P), Math.round(interestEarned)],
                        backgroundColor: ['#1a56db', '#10b981'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: { legend: { position: 'bottom' } }
                }
            });
        }
    }

    if (fdPrincipalInput) {
        fdPrincipalInput.addEventListener('input', calculateFD);
        fdRateInput.addEventListener('input', calculateFD);
        fdTenureInput.addEventListener('input', calculateFD);
        calculateFD();
    }


    // ==========================================
    // 3. RD CALCULATOR
    // ==========================================
    const rdMonthlyInput = document.getElementById('rdMonthly');
    const rdRateInput = document.getElementById('rdRate');
    const rdTenureInput = document.getElementById('rdTenure');
    let rdChart = null;

    function calculateRD() {
        if (!rdMonthlyInput) return;
        const P = parseFloat(rdMonthlyInput.value) || 0;
        const rate = parseFloat(rdRateInput.value) || 0;
        const n = parseInt(rdTenureInput.value) || 0;

        if (P <= 0 || n <= 0) return;

        const totalDeposit = P * n;
        const r = rate / 100.0;
        const interest = (P * n * (n + 1) / 24.0) * r;
        const maturity = totalDeposit + interest;

        document.getElementById('rdMaturityResult').innerText = '₹' + Math.round(maturity).toLocaleString('en-IN');
        document.getElementById('rdInterestResult').innerText = '₹' + Math.round(interest).toLocaleString('en-IN');
        document.getElementById('rdDepositResult').innerText = '₹' + Math.round(totalDeposit).toLocaleString('en-IN');

        const ctx = document.getElementById('rdChart');
        if (ctx) {
            if (rdChart) rdChart.destroy();
            rdChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Total Monthly Deposits', 'Interest Gain'],
                    datasets: [{
                        data: [Math.round(totalDeposit), Math.round(interest)],
                        backgroundColor: ['#0d2346', '#059669'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: { legend: { position: 'bottom' } }
                }
            });
        }
    }

    if (rdMonthlyInput) {
        rdMonthlyInput.addEventListener('input', calculateRD);
        rdRateInput.addEventListener('input', calculateRD);
        rdTenureInput.addEventListener('input', calculateRD);
        calculateRD();
    }


    // ==========================================
    // 4. SIP CALCULATOR
    // ==========================================
    const sipMonthlyInput = document.getElementById('sipMonthly');
    const sipRateInput = document.getElementById('sipRate');
    const sipYearsInput = document.getElementById('sipYears');
    let sipChart = null;

    function calculateSIP() {
        if (!sipMonthlyInput) return;
        const P = parseFloat(sipMonthlyInput.value) || 0;
        const annualReturn = parseFloat(sipRateInput.value) || 0;
        const years = parseInt(sipYearsInput.value) || 0;

        if (P <= 0 || years <= 0) return;

        const i = (annualReturn / 12.0) / 100.0;
        const n = years * 12;
        const totalInvested = P * n;

        // M = P * ((1 + i)^n - 1) / i * (1 + i)
        let totalValue = 0;
        if (i === 0) {
            totalValue = totalInvested;
        } else {
            totalValue = P * ((Math.pow(1 + i, n) - 1) / i) * (1 + i);
        }
        const estimatedReturns = totalValue - totalInvested;

        document.getElementById('sipTotalResult').innerText = '₹' + Math.round(totalValue).toLocaleString('en-IN');
        document.getElementById('sipReturnsResult').innerText = '₹' + Math.round(estimatedReturns).toLocaleString('en-IN');
        document.getElementById('sipInvestedResult').innerText = '₹' + Math.round(totalInvested).toLocaleString('en-IN');

        const ctx = document.getElementById('sipChart');
        if (ctx) {
            if (sipChart) sipChart.destroy();
            sipChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Invested Amount', 'Wealth Gain (Returns)'],
                    datasets: [{
                        data: [Math.round(totalInvested), Math.round(estimatedReturns)],
                        backgroundColor: ['#1a56db', '#10b981'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: { legend: { position: 'bottom' } }
                }
            });
        }
    }

    if (sipMonthlyInput) {
        sipMonthlyInput.addEventListener('input', calculateSIP);
        sipRateInput.addEventListener('input', calculateSIP);
        sipYearsInput.addEventListener('input', calculateSIP);
        calculateSIP();
    }
});

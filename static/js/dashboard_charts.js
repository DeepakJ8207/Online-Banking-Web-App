/**
 * PRIME RESERVE BANK - Dynamic Dashboard Charts Engine
 * Powered by Chart.js & Real-time Django ORM Data
 */

document.addEventListener('DOMContentLoaded', function() {
    const monthlyCtx = document.getElementById('monthlyIncomeExpenseChart');
    const creditDebitCtx = document.getElementById('creditDebitDoughnutChart');
    const categoryCtx = document.getElementById('categorySpendingChart');

    if (!monthlyCtx && !creditDebitCtx && !categoryCtx) return;

    fetch('/dashboard/api/analytics/')
        .then(response => response.json())
        .then(data => {
            // 1. Monthly Income vs Expense Chart (Bar)
            if (monthlyCtx) {
                new Chart(monthlyCtx, {
                    type: 'bar',
                    data: {
                        labels: data.monthly_labels,
                        datasets: [
                            {
                                label: 'Income (Credits ₹)',
                                data: data.monthly_income,
                                backgroundColor: '#10b981',
                                borderRadius: 6,
                                barPercentage: 0.6,
                                categoryPercentage: 0.7
                            },
                            {
                                label: 'Expenses (Debits ₹)',
                                data: data.monthly_expense,
                                backgroundColor: '#1a56db',
                                borderRadius: 6,
                                barPercentage: 0.6,
                                categoryPercentage: 0.7
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'top', labels: { boxWidth: 12, font: { family: 'Plus Jakarta Sans', size: 12 } } },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return `${context.dataset.label}: ₹${context.raw.toLocaleString('en-IN')}`;
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: { color: '#f1f5f9' },
                                ticks: {
                                    callback: function(value) { return '₹' + (value >= 1000 ? (value/1000) + 'k' : value); }
                                }
                            },
                            x: { grid: { display: false } }
                        }
                    }
                });
            }

            // 2. Credit vs Debit Doughnut
            if (creditDebitCtx) {
                const totalMove = data.credit_total + data.debit_total;
                const creditVal = totalMove === 0 ? 50 : data.credit_total;
                const debitVal = totalMove === 0 ? 50 : data.debit_total;

                new Chart(creditDebitCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Total Credits', 'Total Debits'],
                        datasets: [{
                            data: [creditVal, debitVal],
                            backgroundColor: ['#059669', '#dc2626'],
                            borderWidth: 0,
                            hoverOffset: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '72%',
                        plugins: {
                            legend: { position: 'bottom', labels: { boxWidth: 12 } },
                            tooltip: {
                                callbacks: {
                                    label: function(ctx) {
                                        return `${ctx.label}: ₹${ctx.raw.toLocaleString('en-IN')}`;
                                    }
                                }
                            }
                        }
                    }
                });
            }

            // 3. Category Spending Chart
            if (categoryCtx) {
                new Chart(categoryCtx, {
                    type: 'doughnut',
                    data: {
                        labels: data.category_labels,
                        datasets: [{
                            data: data.category_values,
                            backgroundColor: [
                                '#1a56db', '#059669', '#d97706', '#7c3aed', '#db2777', '#0284c7', '#64748b'
                            ],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'right', labels: { boxWidth: 10, font: { size: 11 } } },
                            tooltip: {
                                callbacks: {
                                    label: function(ctx) {
                                        return `${ctx.label}: ₹${ctx.raw.toLocaleString('en-IN')}`;
                                    }
                                }
                            }
                        }
                    }
                });
            }
        })
        .catch(err => console.error("Error loading banking charts:", err));
});

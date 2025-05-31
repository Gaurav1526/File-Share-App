// dashboard.js - Chart initialization
document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts if they exist on the page
    const downloadCtx = document.getElementById('downloadChart');
    const typeCtx = document.getElementById('fileTypeChart');
    
    if (downloadCtx) {
        new Chart(downloadCtx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Downloads',
                    data: [12, 19, 8, 15, 22, 18, 25],
                    borderColor: '#4e73df',
                    backgroundColor: 'rgba(78, 115, 223, 0.05)',
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
    
    if (typeCtx) {
        new Chart(typeCtx, {
            type: 'doughnut',
            data: {
                labels: ['Documents', 'Images', 'Archives', 'Other'],
                datasets: [{
                    data: [45, 25, 15, 15],
                    backgroundColor: ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }
});
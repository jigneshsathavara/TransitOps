document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('demoForm');
  const message = document.getElementById('formMessage');

  if (form && message) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();

      const formData = new FormData(form);
      const payload = {
        name: formData.get('name')?.toString().trim() || '',
        email: formData.get('email')?.toString().trim() || '',
        company: formData.get('company')?.toString().trim() || '',
        message: formData.get('message')?.toString().trim() || ''
      };

      message.textContent = 'Sending your request...';

      try {
        const response = await fetch('/api/contact', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok && data.success) {
          message.textContent = data.message || `Thanks, ${payload.name}! Your request has been received.`;
          form.reset();
        } else {
          message.textContent = data.message || 'Unable to submit your request right now.';
        }
      } catch (error) {
        console.error('Contact form submission failed:', error);
        message.textContent = 'Unable to submit your request right now.';
      }
    });
  }

  const chatToggle = document.getElementById('chatToggle');
  const chatClose = document.getElementById('chatClose');
  const chatbotPanel = document.getElementById('chatbotPanel');
  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatbotForm');
  const chatInput = document.getElementById('chatInput');

  const addMessage = (text, sender) => {
    const bubble = document.createElement('div');
    bubble.className = `message ${sender}`;
    bubble.textContent = text;
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  };

  const getBotReply = (text) => {
    const normalized = text.toLowerCase();

    if (normalized.includes('route') || normalized.includes('trip')) {
      return 'I can help review active routes, dispatch priorities, and vehicle coverage.';
    }

    if (normalized.includes('alert') || normalized.includes('issue')) {
      return 'Our system can flag delays, maintenance warnings, and fuel threshold alerts in real time.';
    }

    if (normalized.includes('demo') || normalized.includes('price') || normalized.includes('plan')) {
      return 'We can arrange a tailored demo for your fleet operations team.';
    }

    if (normalized.includes('hello') || normalized.includes('hi')) {
      return 'Hello! I can help with routes, alerts, and platform demos.';
    }

    return 'Thanks for reaching out. Ask me about routes, alerts, or booking a demo.';
  };

  if (chatToggle && chatClose && chatbotPanel && chatMessages && chatForm && chatInput) {
    addMessage('Hello! I can help with routes, alerts, and platform demos.', 'bot');

    chatToggle.addEventListener('click', () => {
      chatbotPanel.classList.toggle('open');
      if (chatbotPanel.classList.contains('open')) {
        chatInput.focus();
      }
    });

    chatClose.addEventListener('click', () => {
      chatbotPanel.classList.remove('open');
    });

    chatForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const userText = chatInput.value.trim();

      if (!userText) return;

      addMessage(userText, 'user');
      chatInput.value = '';

      window.setTimeout(() => {
        addMessage(getBotReply(userText), 'bot');
      }, 450);
    });
  }

  // ===== DARK MODE TOGGLE =====
  const initDarkMode = () => {
    const darkModeToggle = document.querySelector('.dark-mode-toggle');
    const savedMode = localStorage.getItem('transitops-dark-mode') === 'true';

    if (savedMode) {
      document.body.classList.add('dark-mode');
    }

    if (darkModeToggle) {
      darkModeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDarkMode = document.body.classList.contains('dark-mode');
        localStorage.setItem('transitops-dark-mode', isDarkMode);
        darkModeToggle.textContent = isDarkMode ? '☀️' : '🌙';
      });

      // Set initial icon
      darkModeToggle.textContent = savedMode ? '☀️' : '🌙';
    }
  };

  initDarkMode();

  // ===== ANALYTICS INITIALIZATION =====
  const initAnalytics = async () => {
    try {
      const response = await fetch('/api/analytics/dashboard');
      const data = await response.json();

      if (data.success) {
        // Update KPI cards
        const vehicleStats = data.vehicle_stats || [];
        const availableVehicles = vehicleStats.find(s => s.status === 'Available')?.total || 0;
        const totalVehicles = vehicleStats.reduce((sum, s) => sum + s.total, 0);

        // Display analytics
        console.log('Dashboard Analytics:', data);
      }
    } catch (error) {
      console.error('Failed to load analytics:', error);
    }
  };

  // Call analytics on dashboard page
  if (window.location.pathname.includes('dashboard')) {
    initAnalytics();
  }

  // ===== SEARCH & FILTER =====
  window.searchVehicles = async (query, status, type) => {
    try {
      const params = new URLSearchParams();
      if (query) params.append('q', query);
      if (status) params.append('status', status);
      if (type) params.append('type', type);

      const response = await fetch(`/api/vehicles/search?${params}`);
      const data = await response.json();

      if (data.success) {
        console.log('Search results:', data.data);
        return data.data;
      }
    } catch (error) {
      console.error('Search failed:', error);
    }
    return [];
  };

  window.searchDrivers = async (query, status) => {
    try {
      const params = new URLSearchParams();
      if (query) params.append('q', query);
      if (status) params.append('status', status);

      const response = await fetch(`/api/drivers/search?${params}`);
      const data = await response.json();

      if (data.success) {
        console.log('Driver search results:', data.data);
        return data.data;
      }
    } catch (error) {
      console.error('Driver search failed:', error);
    }
    return [];
  };

  // ===== DOCUMENT UPLOAD =====
  window.uploadVehicleDocument = async (vehicleId, file, docType, expiryDate) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('type', docType);
      if (expiryDate) formData.append('expiry_date', expiryDate);

      const response = await fetch(`/api/documents/vehicle/${vehicleId}`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      return data.success;
    } catch (error) {
      console.error('Document upload failed:', error);
      return false;
    }
  };

  window.uploadDriverDocument = async (driverId, file, docType, expiryDate) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('type', docType);
      if (expiryDate) formData.append('expiry_date', expiryDate);

      const response = await fetch(`/api/documents/driver/${driverId}`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      return data.success;
    } catch (error) {
      console.error('Document upload failed:', error);
      return false;
    }
  };

  // ===== PDF EXPORT =====
  window.exportReportPDF = async (reportType) => {
    try {
      const response = await fetch('/api/export/report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ type: reportType })
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `TransitOps_${reportType}_Report.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        return true;
      }
    } catch (error) {
      console.error('PDF export failed:', error);
    }
    return false;
  };

  // ===== EMAIL REMINDERS =====
  window.sendLicenseExpiryReminders = async () => {
    try {
      const response = await fetch('/api/reminders/check-expiring-licenses', {
        method: 'POST'
      });

      const data = await response.json();
      if (data.success) {
        console.log(`License reminders sent: ${data.reminders_sent}`);
        return data.reminders_sent;
      }
    } catch (error) {
      console.error('Failed to send license reminders:', error);
    }
    return 0;
  };

  // ===== CHART INITIALIZATION (Chart.js support) =====
  window.initChart = (canvasId, chartType, labels, datasets) => {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) return;

    const ctx = canvas.getContext('2d');
    new window.Chart(ctx, {
      type: chartType,
      data: {
        labels: labels,
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: document.body.classList.contains('dark-mode') ? '#f1f5f9' : '#1f2937'
            }
          }
        },
        scales: {
          y: {
            ticks: {
              color: document.body.classList.contains('dark-mode') ? '#cbd5e1' : '#6b7280'
            },
            grid: {
              color: document.body.classList.contains('dark-mode') ? 'rgba(99, 102, 241, 0.1)' : 'rgba(0, 0, 0, 0.1)'
            }
          },
          x: {
            ticks: {
              color: document.body.classList.contains('dark-mode') ? '#cbd5e1' : '#6b7280'
            },
            grid: {
              color: document.body.classList.contains('dark-mode') ? 'rgba(99, 102, 241, 0.1)' : 'rgba(0, 0, 0, 0.1)'
            }
          }
        }
      }
    });
  };

  // ===== FILTER HELPERS =====
  const searchBox = document.querySelector('.search-box input');
  const filterButton = document.querySelector('.filter-button');
  const sortButton = document.querySelector('.sort-button');

  if (searchBox) {
    searchBox.addEventListener('input', (e) => {
      const query = e.target.value;
      console.log('Searching for:', query);
      // Trigger search based on context
    });
  }

  if (filterButton) {
    filterButton.addEventListener('click', () => {
      console.log('Opening filter menu');
      // Show filter options
    });
  }

  if (sortButton) {
    sortButton.addEventListener('click', () => {
      console.log('Opening sort menu');
      // Show sort options
    });
  }
});

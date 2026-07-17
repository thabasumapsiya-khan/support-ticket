document.addEventListener('DOMContentLoaded', () => {
  const subjectInput = document.getElementById('subject');
  const bodyInput = document.getElementById('body');
  const analyzeTicketButton = document.getElementById('analyze-ticket');
  const resultBox = document.getElementById('result-box');
  const batchFileInput = document.getElementById('batch-file');
  const analyzeBatchButton = document.getElementById('analyze-batch');
  const batchResults = document.getElementById('batch-results');
  const loadPreviousTicketsButton = document.getElementById('load-previous-tickets');
  const previousTickets = document.getElementById('previous-tickets');

  const renderPreviousTickets = (tickets) => {
    if (!tickets.length) {
      previousTickets.innerHTML = '<p class="empty-state">No tickets have been processed yet.</p>';
      return;
    }

    previousTickets.innerHTML = '';
    tickets.slice().reverse().forEach((ticket) => {
      const card = document.createElement('div');
      card.className = 'ticket-card';
      card.innerHTML = `
        <h3>${ticket.subject || 'Untitled Ticket'}</h3>
        <p><strong>Category:</strong> ${ticket.category || '-'}</p>
        <p><strong>Urgency:</strong> ${ticket.urgency || '-'}</p>
        <p><strong>Assigned Team:</strong> ${ticket.team || '-'}</p>
        <p><strong>Confidence:</strong> ${ticket.confidence ?? '-'}</p>
        <p><strong>Timestamp:</strong> ${ticket.timestamp || '-'}</p>
        <p><strong>Reason:</strong> ${ticket.reason || '-'}</p>
      `;
      previousTickets.appendChild(card);
    });
  };

  analyzeTicketButton.addEventListener('click', async () => {
    const subject = subjectInput.value.trim();
    const body = bodyInput.value.trim();

    if (!subject || !body) {
      alert('Please enter both a subject and description.');
      return;
    }

    try {
      const response = await fetch('/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject, body }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to classify ticket');
      }

      const data = await response.json();
      resultBox.innerHTML = `
        <p><strong>Category:</strong> ${data.category}</p>
        <p><strong>Urgency:</strong> ${data.urgency}</p>
        <p><strong>Confidence:</strong> ${data.confidence}</p>
        <p><strong>Assigned Team:</strong> ${data.team}</p>
        <p><strong>Reason:</strong> ${data.reason}</p>
      `;
      await loadPreviousTickets();
    } catch (error) {
      resultBox.innerHTML = `<p>${error.message}</p>`;
      console.error(error);
    }
  });

  analyzeBatchButton.addEventListener('click', async () => {
    const file = batchFileInput.files[0];

    if (!file) {
      alert('Please choose a JSON file first.');
      return;
    }

    try {
      const text = await file.text();
      const tickets = JSON.parse(text);

      const response = await fetch('/classify-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tickets),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to classify batch');
      }

      const data = await response.json();
      batchResults.innerHTML = '';
      await loadPreviousTickets();

      data.forEach((ticket, index) => {
        const card = document.createElement('div');
        card.className = 'ticket-card';
        card.innerHTML = `
          <h3>Ticket #${index + 1}</h3>
          <p><strong>Category:</strong> ${ticket.category}</p>
          <p><strong>Urgency:</strong> ${ticket.urgency}</p>
          <p><strong>Team:</strong> ${ticket.team}</p>
          <p><strong>Reason:</strong> ${ticket.reason}</p>
        `;
        batchResults.appendChild(card);
      });
    } catch (error) {
      batchResults.innerHTML = `<p>${error.message}</p>`;
      console.error(error);
    }
  });

  const loadPreviousTickets = async () => {
    try {
      const response = await fetch('/tickets', { cache: 'no-store' });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to load previous tickets');
      }

      const data = await response.json();
      renderPreviousTickets(data);
    } catch (error) {
      previousTickets.innerHTML = `<p>${error.message}</p>`;
      console.error(error);
    }
  };

  loadPreviousTicketsButton.addEventListener('click', () => {
    loadPreviousTickets();
  });

  loadPreviousTickets();
});

const express = require('express');
const cors = require('cors');
const mysql = require('mysql2/promise');
const nodemailer = require('nodemailer');
const dotenv = require('dotenv');

dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

const getDbConfig = () => {
  const dbUri = process.env.DB_URI;
  if (dbUri) {
    const parsed = new URL(dbUri);
    return {
      host: parsed.hostname,
      port: parsed.port || 3306,
      user: decodeURIComponent(parsed.username || process.env.DB_USER || 'root'),
      password: decodeURIComponent(parsed.password || process.env.DB_PASSWORD || ''),
      database: parsed.pathname.replace(/^\/+/, '') || process.env.DB_NAME || 'transitops'
    };
  }

  return {
    host: process.env.DB_HOST || 'localhost',
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || '',
    database: process.env.DB_NAME || 'transitops'
  };
};

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.post('/api/contact', async (req, res) => {
  const { name, email, company, message } = req.body;

  if (!name || !email || !company) {
    return res.status(400).json({ success: false, message: 'Please fill all required fields.' });
  }

  let connection;
  try {
    connection = await mysql.createConnection(getDbConfig());

    await connection.execute(
      'INSERT INTO contact_requests (full_name, email, company, message) VALUES (?, ?, ?, ?)',
      [name, email, company, message || '']
    );

    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: process.env.ADMIN_EMAIL,
        pass: process.env.APP_PASSWORD
      }
    });

    const mailOptions = {
      from: process.env.ADMIN_EMAIL,
      to: process.env.ADMIN_EMAIL,
      subject: 'New TransitOps Contact Request',
      html: `
        <h3>New contact request received</h3>
        <p><strong>Name:</strong> ${name}</p>
        <p><strong>Email:</strong> ${email}</p>
        <p><strong>Company:</strong> ${company}</p>
        <p><strong>Message:</strong> ${message || 'No message provided'}</p>
      `
    };

    await transporter.sendMail(mailOptions);

    res.json({ success: true, message: 'Your request has been saved and the admin has been notified.' });
  } catch (error) {
    console.error('Contact submission failed:', error);
    res.status(500).json({ success: false, message: 'Failed to submit contact request.' });
  } finally {
    if (connection) await connection.end();
  }
});

app.get('/', (req, res) => {
  res.send('TransitOps contact API is running.');
});

app.listen(port, () => {
  console.log(`Server running on http://localhost:${port}`);
});

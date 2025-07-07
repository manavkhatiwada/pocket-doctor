const express = require("express");
const bodyParser = require("body-parser");
const path = require("path");

const app = express();
const PORT = 3003;

// Middleware
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, "public"))); // For serving CSS and static files

// ROUTES

// Appointment Page
app.get("/appointment", (req, res) => {
  res.sendFile(path.join(__dirname, "views", "appointment.html"));
});

// Home Page
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "views", "home.html"));
});

// Chat Page
app.get("/chat", (req, res) => {
  res.sendFile(path.join(__dirname, "views", "chat.html"));
});

// Login Page
app.get("/login", (req, res) => {
  res.sendFile(path.join(__dirname, "views", "login.html"));
});

// Signup Page
app.get("/signup", (req, res) => {
  res.sendFile(path.join(__dirname, "views", "signup.html"));
});

// About Page
app.get("/about", (req, res) => {
  res.sendFile(path.join(__dirname, "views", "about.html"));
});

// POST Appointment
app.post("/appointment", (req, res) => {
  const { name, email, phone, department, doctor, problem, date, time } = req.body;
  console.log("Appointment:", req.body);

  res.send(`
    <h2>Appointment booked for ${name} on ${date} at ${time}!</h2>
    <p>Department: ${department}<br>Doctor: ${doctor}<br>Issue: ${problem}</p>
    <a href="/">Go Home</a>
  `);
});

// 404 Route
app.get("*", (req, res) => {
  res.status(404).send("Page not found");
});

// Start Server
app.listen(PORT, () => {
  console.log(`✅ Server running at http://localhost:${PORT}`);
});

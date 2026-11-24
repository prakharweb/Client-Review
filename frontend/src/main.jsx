
import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Star, Heart, MessageSquare, ShieldCheck,
  ExternalLink, CheckCircle2, LogOut
} from "lucide-react";
import "./style.css";

const API = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

const GOOGLE_URL_FALLBACK =
  "https://g.page/r/CSLhXGE7iSkSEAE/review";

// Safe JSON response handler
async function safeJson(response) {
  const text = await response.text();

  if (!text) {
    throw new Error(
      `Empty server response. HTTP ${response.status}`
    );
  }

  let data;

  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(
      `Server returned invalid JSON. HTTP ${response.status}. Check API URL and backend deployment.`
    );
  }

  if (!response.ok) {
    throw new Error(
      data.detail || data.message || `HTTP Error ${response.status}`
    );
  }

  return data;
}

// API helper
async function apiRequest(path, options = {}) {
  if (!API) {
    throw new Error(
      "Backend API URL missing. Set VITE_API_URL in Render frontend environment."
    );
  }

  const response = await fetch(`${API}${path}`, options);
  return safeJson(response);
}

function App() {
  const [rating, setRating] = useState(0);
  const [googleUrl, setGoogleUrl] = useState(GOOGLE_URL_FALLBACK);
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [admin, setAdmin] = useState(
    window.location.pathname === "/admin"
  );

  const [token, setToken] = useState(
    sessionStorage.getItem("adminToken") || ""
  );

  const [rows, setRows] = useState([]);
  const [stats, setStats] = useState(null);
  const [adminError, setAdminError] = useState("");

  // Load Google review URL
  useEffect(() => {
    apiRequest("/api/config")
      .then(data => {
        if (data.google_review_url) {
          setGoogleUrl(data.google_review_url);
        }
      })
      .catch(err => {
        console.error("Config API error:", err);
      });
  }, []);

  // Handle browser navigation
  useEffect(() => {
    const onPop = () => {
      setAdmin(window.location.pathname === "/admin");
    };

    window.addEventListener("popstate", onPop);

    return () => {
      window.removeEventListener("popstate", onPop);
    };
  }, []);

  // Admin dashboard data
  async function loadAdmin(t = token) {
    setAdminError("");

    try {
      const headers = {
        Authorization: `Bearer ${t}`
      };

      const [feedbackData, statsData] = await Promise.all([
        apiRequest("/api/admin/feedback", { headers }),
        apiRequest("/api/admin/stats", { headers })
      ]);

      setRows(feedbackData);
      setStats(statsData);

      sessionStorage.setItem("adminToken", t);
      setToken(t);

    } catch (err) {
      setAdminError(err.message);
      setStats(null);
    }
  }

  // Submit customer feedback
  async function submit(e) {
    e.preventDefault();

    setError("");

    if (!rating) {
      setError("Please select your star rating.");
      return;
    }

    setBusy(true);

    const form = new FormData(e.currentTarget);

    const payload = {
      name: form.get("name"),
      organization: form.get("organization") || null,
      email: form.get("email"),
      phone: form.get("phone") || null,
      rating: rating,
      message: form.get("message")
    };

    try {
      const data = await apiRequest("/api/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      if (!data.success) {
        throw new Error("Feedback submission failed.");
      }

      setSubmitted(true);

      console.log("Feedback submitted:", data);

      // After feedback is saved and the email notification attempt completes,
      // open the Google review page. The Google review option remains available
      // for every rating.
      window.location.assign(googleUrl);

      if (!data.email_sent) {
        console.warn(
          "Feedback saved, but Brevo email was not sent:",
          data.email_status
        );
      }

    } catch (err) {
      console.error("Feedback error:", err);
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  // Admin logout
  function logout() {
    sessionStorage.removeItem("adminToken");
    setToken("");
    setStats(null);
    setRows([]);
    setAdminError("");
  }

  // Admin dashboard
  if (admin) {
    return (
      <main className="admin-wrap">

        <div className="admin-head">
          <div>
            <div className="eyebrow">REVIEW MANAGEMENT</div>
            <h1>Feedback Dashboard</h1>
          </div>

          <button className="secondary" onClick={logout}>
            <LogOut size={16} /> Logout
          </button>
        </div>

        {!stats ? (
          <section className="panel login">
            <h2>Admin Sign In</h2>
            <p>Enter your backend ADMIN_TOKEN.</p>

            <form
              onSubmit={e => {
                e.preventDefault();

                const t = new FormData(e.currentTarget).get("token");

                loadAdmin(t);
              }}
            >
              <input
                name="token"
                type="password"
                placeholder="Admin token"
                required
              />

              <button className="primary">
                Sign In
              </button>
            </form>

            {adminError && (
              <p className="error">{adminError}</p>
            )}
          </section>
        ) : (
          <>
            <div className="stats">

              <div className="stat">
                <span>Total Feedback</span>
                <b>{stats.total}</b>
              </div>

              <div className="stat">
                <span>Average Rating</span>
                <b>{stats.average_rating} / 5</b>
              </div>

              {[5, 4, 3, 2, 1].map(n => (
                <div className="stat" key={n}>
                  <span>{n} Star</span>
                  <b>{stats.distribution[n]}</b>
                </div>
              ))}

            </div>

            <section className="panel">
              <h2>Recent Submissions</h2>

              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Name</th>
                      <th>Organization</th>
                      <th>Contact</th>
                      <th>Rating</th>
                      <th>Feedback</th>
                    </tr>
                  </thead>

                  <tbody>
                    {rows.map(x => (
                      <tr key={x.id}>
                        <td>
                          {new Date(
                            x.created_at.endsWith("Z")
                              ? x.created_at
                              : x.created_at + "Z"
                          ).toLocaleString()}
                        </td>

                        <td>{x.name}</td>
                        <td>{x.organization || "—"}</td>

                        <td>
                          {x.email}
                          <br />
                          {x.phone || "—"}
                        </td>

                        <td>
                          {"★".repeat(x.rating)}
                          {"☆".repeat(5 - x.rating)}
                        </td>

                        <td>{x.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {!rows.length && (
                  <p>No feedback submitted yet.</p>
                )}
              </div>
            </section>
          </>
        )}
      </main>
    );
  }

  // Customer review page
  return (
    <main className="page">

      <header className="top">
        <div className="brand">
          <div className="brand-icon">
            <Heart size={19} />
          </div>

          <span>We value your feedback</span>
        </div>

        <span className="secure">
          <ShieldCheck size={15} />
          Secure feedback
        </span>
      </header>

      <section className="hero">

        <div className="eyebrow">
          YOUR EXPERIENCE MATTERS
        </div>

        <h1>
          How was your
          <br />
          <em>experience?</em>
        </h1>

        <p>
          Your feedback helps us improve and serve you better.
          It only takes a minute.
        </p>

        <div className="review-card">

          {submitted ? (
            <div className="success">
              <CheckCircle2 size={48} />

              <h2>Thank you for your feedback!</h2>

              <p>
                Your response has been submitted successfully.
                We appreciate your time.
              </p>

              <button
                className="primary"
                onClick={() => {
                  setSubmitted(false);
                  setRating(0);
                }}
              >
                Submit another response
              </button>
            </div>
          ) : (
            <>
              <h2>Rate your experience</h2>

              <p className="muted">
                Choose a rating from 1 to 5 stars
              </p>

              <div
                className="stars"
                role="radiogroup"
                aria-label="Rating"
              >
                {[1, 2, 3, 4, 5].map(n => (
                  <button
                    type="button"
                    key={n}
                    aria-label={`${n} stars`}
                    aria-checked={rating === n}
                    role="radio"
                    className={
                      rating >= n
                        ? "star active"
                        : "star"
                    }
                    onClick={() => setRating(n)}
                  >
                    <Star
                      size={34}
                      fill={
                        rating >= n
                          ? "currentColor"
                          : "none"
                      }
                    />
                  </button>
                ))}
              </div>

              <div className="rating-label">
                {rating
                  ? [
                      "",
                      "We're sorry to hear that",
                      "We'll work to improve",
                      "Thanks for letting us know",
                      "Glad you had a good experience!",
                      "Wonderful! Thank you!"
                    ][rating]
                  : "Tap a star to rate us"}
              </div>

              {rating > 0 && (
                <div className="next-step">

                  {rating >= 4 ? (
                    <div className="google-prompt">
                      <div className="google-mark">G</div>

                      <div>
                        <b>
                          Would you share your experience on Google?
                        </b>

                        <p className="muted">
                          Your honest public review helps others
                          discover us.
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="private-prompt">
                      <MessageSquare size={20} />

                      <div>
                        <b>Tell us how we can do better</b>

                        <p className="muted">
                          Your feedback goes directly to our team.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Google review link available to all customers */}
                  <a
                    className="google-button"
                    href={googleUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <ExternalLink size={17} />
                    Write or view a Google review
                  </a>

                  {rating >= 4 ? (
                    <button
                      type="button"
                      className="primary full"
                      onClick={() => window.location.assign(googleUrl)}
                    >
                      Submit
                    </button>
                  ) : (
                    <>
                      <div className="form-divider">
                        <span>SHARE PRIVATE FEEDBACK</span>
                      </div>

                      <form
                        onSubmit={submit}
                        className="feedback-form"
                      >
                        <div className="field">
                          <label>Full name *</label>
                          <input
                            name="name"
                            placeholder="Your name"
                            minLength="2"
                            maxLength="160"
                            required
                          />
                        </div>

                        <div className="field">
                          <label>Hospital / Company</label>
                          <input
                            name="organization"
                            placeholder="Organization name"
                            maxLength="200"
                          />
                        </div>

                        <div className="two">
                          <div className="field">
                            <label>Email address *</label>
                            <input
                              name="email"
                              type="email"
                              placeholder="you@example.com"
                              required
                            />
                          </div>

                          <div className="field">
                            <label>Mobile number</label>
                            <input
                              name="phone"
                              type="tel"
                              placeholder="+91"
                              maxLength="40"
                            />
                          </div>
                        </div>

                        <div className="field">
                          <label>Your feedback *</label>
                          <textarea
                            name="message"
                            placeholder="Tell us about your experience..."
                            minLength="3"
                            maxLength="5000"
                            rows="4"
                            required
                          />
                        </div>

                        <button
                          className="primary full"
                          disabled={busy}
                        >
                          {busy ? "Submitting..." : "Submit feedback"}
                        </button>

                        {error && <p className="error">{error}</p>}
                      </form>
                    </>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        <div className="trust">
          <ShieldCheck size={16} />
          Your feedback is shared securely with our team.
        </div>

      </section>

      <footer>
        Made with care · Customer Experience
      </footer>

    </main>
  );
}

createRoot(document.getElementById("root")).render(
  <App />
);

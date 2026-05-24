import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { CheckCircle2, Loader2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const fmt = (n) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n || 0);

const FONT_STACK = "'Helvetica Neue', Helvetica, Arial, sans-serif";

export default function AcceptPage() {
  const { token } = useParams();
  const [state, setState] = useState({ loading: true });
  const [accepted, setAccepted] = useState(false);
  const [note, setNote] = useState("");
  const [checked, setChecked] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const { data } = await axios.get(`${API}/public/accept/${token}`);
        if (!alive) return;
        setState({ loading: false, data });
        if (data.already_accepted) setAccepted(true);
      } catch (e) {
        if (!alive) return;
        setState({
          loading: false,
          error:
            e.response?.status === 404
              ? "This estimate link is invalid or has expired."
              : `Could not load the estimate. ${e.response?.data?.detail || e.message}`,
        });
      }
    })();
    return () => { alive = false; };
  }, [token]);

  const submit = async () => {
    if (!checked || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const { data } = await axios.post(`${API}/public/accept/${token}`, {
        note: note.trim() || null,
      });
      setAccepted(true);
      setState((s) => ({
        ...s,
        data: { ...s.data, company_name: data.company_name, accepted_at: data.accepted_at },
      }));
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (state.loading) {
    return (
      <Wrap>
        <div style={{ textAlign: "center", padding: "60px 0", color: "#71717A" }}>
          <Loader2 className="animate-spin" style={{ display: "inline-block", marginRight: 8 }} />
          Loading your estimate…
        </div>
      </Wrap>
    );
  }

  if (state.error) {
    return (
      <Wrap>
        <div style={{ padding: 32, textAlign: "center" }}>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: "#09090B" }}>Estimate Not Found</h1>
          <p style={{ color: "#52525B", marginTop: 12 }}>{state.error}</p>
        </div>
      </Wrap>
    );
  }

  const d = state.data;

  if (accepted) {
    return (
      <Wrap company={d}>
        <div style={{ padding: 32, textAlign: "center" }} data-testid="accept-success">
          <CheckCircle2 size={64} color="#16A34A" style={{ margin: "0 auto" }} />
          <h1 style={{ fontSize: 28, fontWeight: 800, color: "#09090B", marginTop: 16 }}>
            You're all set, {d.customer_name?.split(" ")[0] || "there"}.
          </h1>
          <p style={{ fontSize: 16, color: "#52525B", marginTop: 12, lineHeight: 1.6 }}>
            We've notified <strong style={{ color: "#09090B" }}>{d.company_name}</strong> that
            you accepted estimate <strong style={{ color: "#09090B" }}>{d.estimate_number}</strong> for{" "}
            <strong style={{ color: "#09090B" }}>{fmt(d.total)}</strong>.
          </p>
          <p style={{ fontSize: 14, color: "#71717A", marginTop: 16 }}>
            They'll reach out within one business day to schedule next steps.
          </p>
        </div>
      </Wrap>
    );
  }

  return (
    <Wrap company={d}>
      <div style={{ padding: 32 }} data-testid="accept-page">
        <div
          style={{
            fontSize: 11, fontWeight: 700, letterSpacing: 2,
            textTransform: "uppercase", color: "#F97316", marginBottom: 8,
          }}
        >
          Confirm Acceptance
        </div>
        <h1 style={{ fontSize: 26, fontWeight: 800, color: "#09090B", margin: 0 }}>
          Accept Estimate {d.estimate_number}
        </h1>
        <p style={{ fontSize: 15, color: "#52525B", marginTop: 8, lineHeight: 1.6 }}>
          From <strong style={{ color: "#09090B" }}>{d.company_name}</strong> · {d.estimate_date}
        </p>

        <div
          style={{
            marginTop: 24, padding: 24, background: "#FAFAFA",
            borderTop: "4px solid #09090B", borderBottom: "1px solid #E4E4E7",
            display: "flex", justifyContent: "space-between", alignItems: "baseline",
          }}
        >
          <div style={{ fontSize: 20, fontWeight: 800, color: "#09090B" }}>Total Price</div>
          <div
            style={{
              fontSize: 32, fontWeight: 900, color: "#09090B",
              letterSpacing: "-0.5px", fontVariantNumeric: "tabular-nums",
            }}
            data-testid="accept-total"
          >
            {fmt(d.total)}
          </div>
        </div>

        {d.customer_name ? (
          <div style={{ marginTop: 16, fontSize: 13, color: "#52525B" }}>
            <strong style={{ color: "#09090B" }}>Prepared for:</strong> {d.customer_name}
            {d.address ? ` · ${d.address}` : ""}
          </div>
        ) : null}

        <div style={{ marginTop: 28 }}>
          <label
            style={{
              fontSize: 10, fontWeight: 700, letterSpacing: 2,
              textTransform: "uppercase", color: "#A1A1AA", display: "block", marginBottom: 6,
            }}
            htmlFor="customer-note"
          >
            Optional note for the contractor
          </label>
          <textarea
            id="customer-note"
            rows={4}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. Can we start next week? Or, please bring extra trim samples."
            style={{
              width: "100%", padding: 12, border: "1px solid #E4E4E7",
              fontFamily: FONT_STACK, fontSize: 14, color: "#09090B",
              background: "#FFFFFF", resize: "vertical", boxSizing: "border-box",
            }}
            data-testid="accept-note"
          />
        </div>

        <label
          style={{
            marginTop: 20, display: "flex", alignItems: "flex-start", gap: 10,
            fontSize: 15, color: "#09090B", cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
            style={{ width: 18, height: 18, marginTop: 2, accentColor: "#F97316" }}
            data-testid="accept-checkbox"
          />
          <span>
            I, {d.customer_name || "the customer"}, accept this estimate for{" "}
            <strong>{fmt(d.total)}</strong> as quoted by {d.company_name}.
          </span>
        </label>

        {error ? (
          <div style={{ marginTop: 12, color: "#DC2626", fontSize: 13 }}>{error}</div>
        ) : null}

        <button
          type="button"
          onClick={submit}
          disabled={!checked || submitting}
          style={{
            marginTop: 24, width: "100%", padding: "16px 24px",
            fontFamily: FONT_STACK, fontSize: 14, fontWeight: 700,
            letterSpacing: 1.5, textTransform: "uppercase",
            color: "#FFFFFF", background: !checked || submitting ? "#A1A1AA" : "#F97316",
            border: "none", cursor: !checked || submitting ? "not-allowed" : "pointer",
            transition: "background 0.15s",
          }}
          data-testid="accept-submit"
        >
          {submitting ? "Sending acceptance…" : "Confirm Acceptance →"}
        </button>
        <p style={{ marginTop: 14, fontSize: 11, color: "#A1A1AA", textAlign: "center" }}>
          By accepting, you authorize {d.company_name} to begin scheduling. You can still
          reply to the original email with any changes.
        </p>
      </div>
    </Wrap>
  );
}

function Wrap({ children, company }) {
  return (
    <div
      style={{
        minHeight: "100vh", background: "#F4F4F5",
        fontFamily: FONT_STACK, color: "#09090B",
        padding: "32px 12px", boxSizing: "border-box",
      }}
    >
      <div
        style={{
          maxWidth: 560, margin: "0 auto", background: "#FFFFFF",
          border: "1px solid #09090B",
        }}
      >
        {company ? (
          <div style={{
            padding: "20px 32px", borderBottom: "4px solid #F97316",
            display: "flex", alignItems: "center", gap: 12,
          }}>
            {company.company_logo_url ? (
              <img
                src={`${process.env.REACT_APP_BACKEND_URL}${company.company_logo_url}`}
                alt=""
                style={{ height: 40, width: "auto", maxWidth: 160 }}
              />
            ) : null}
            <div style={{ fontSize: 18, fontWeight: 800, color: "#09090B" }}>
              {company.company_name}
            </div>
          </div>
        ) : null}
        {children}
      </div>
      <p style={{ textAlign: "center", marginTop: 18, fontSize: 11, color: "#A1A1AA" }}>
        Secure customer-acceptance link.
      </p>
    </div>
  );
}

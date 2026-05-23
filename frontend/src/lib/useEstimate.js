import { useEffect, useState, useCallback } from "react";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";

export default function useEstimate(id) {
  const [est, setEst] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [emailStatus, setEmailStatus] = useState({ configured: false });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [e, c, em] = await Promise.all([
          api.get(`/estimates/${id}`),
          api.get(`/catalog`),
          api.get(`/email/status`),
        ]);
        if (cancelled) return;
        const savedByKey = {};
        (e.data.lines || []).forEach((l) => {
          savedByKey[`${l.section}::${l.name}`] = l.qty;
        });
        const merged = [];
        c.data.sections.forEach((s) =>
          s.items.forEach((it) => {
            const key = `${s.title}::${it.name}`;
            merged.push({
              section: s.title,
              name: it.name,
              unit: it.unit,
              mat: it.mat,
              lab: it.lab,
              qty: savedByKey[key] || 0,
            });
          })
        );
        setEst({ ...e.data, lines: merged });
        setCatalog(c.data.sections);
        setEmailStatus(em.data);
      } catch (err) {
        toast.error(formatApiError(err.response?.data?.detail));
        setEst(false);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const update = useCallback((patch) => {
    setEst((e) => ({ ...e, ...patch }));
  }, []);

  const updateLineQty = useCallback((section, name, qty) => {
    setEst((e) => ({
      ...e,
      lines: e.lines.map((l) =>
        l.section === section && l.name === name ? { ...l, qty: Number(qty) || 0 } : l
      ),
    }));
  }, []);

  const save = useCallback(async () => {
    if (!est) return;
    try {
      const payload = {
        customer_name: est.customer_name || "",
        address: est.address || "",
        estimate_number: est.estimate_number || "",
        estimate_date: est.estimate_date || "",
        estimator: est.estimator || "",
        notes: est.notes || "",
        waste_pct: est.waste_pct || 0,
        tax_enabled: !!est.tax_enabled,
        tax_rate: est.tax_rate || 0,
        margin_pct: est.margin_pct || 0,
        lines: est.lines.filter((l) => (l.qty || 0) > 0),
        misc_labor: est.misc_labor || [],
        misc_material: est.misc_material || [],
        photos: est.photos || [],
        status_label: est.status_label || "draft",
      };
      const { data } = await api.put(`/estimates/${id}`, payload);
      toast.success("Saved");
      return data;
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  }, [est, id]);

  return { est, catalog, loading, emailStatus, update, updateLineQty, save };
}

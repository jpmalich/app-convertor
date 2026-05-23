import React, { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Copy, RefreshCw, Building2 } from "lucide-react";

export default function Team() {
  const [company, setCompany] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/company");
        setCompany(data);
      } catch (e) {
        toast.error(formatApiError(e.response?.data?.detail));
      }
    })();
  }, []);

  if (!company) return <div className="p-10 text-center text-[#52525B]">Loading…</div>;

  const copyInvite = () => {
    navigator.clipboard.writeText(company.invite_code);
    toast.success("Invite code copied");
  };

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="team-page">
      <div className="text-xs uppercase tracking-[0.2em] text-[#A1A1AA] mb-1">Settings</div>
      <h1 className="font-heading text-4xl text-[#09090B] mb-8">Company &amp; Team</h1>

      <div className="card p-6 mb-6 max-w-2xl">
        <div className="flex items-center gap-3 mb-4">
          <Building2 className="w-5 h-5 text-[#F97316]" />
          <div className="section-tag">Company</div>
        </div>
        <div className="text-2xl font-heading text-[#09090B] mb-1" data-testid="company-name">
          {company.name}
        </div>
        <div className="text-xs text-[#A1A1AA]">
          Created {new Date(company.created_at).toLocaleDateString()}
        </div>
      </div>

      <div className="card p-6 max-w-2xl">
        <div className="section-tag mb-3">Invite a teammate</div>
        <p className="text-sm text-[#52525B] mb-4">
          Share this code so a teammate can join your company. They&apos;ll see the same estimates and price catalog as you.
        </p>
        <div className="flex items-stretch gap-2">
          <div
            className="flex-1 bg-[#09090B] text-[#F97316] font-mono-num text-2xl tracking-[0.3em] px-5 flex items-center"
            data-testid="invite-code-display"
          >
            {company.invite_code}
          </div>
          <button className="btn-primary" onClick={copyInvite} data-testid="copy-invite-btn">
            <Copy className="w-4 h-4" /> Copy
          </button>
        </div>
        <p className="text-xs text-[#A1A1AA] mt-3 uppercase tracking-wider">
          Teammate registers at <span className="font-mono-num text-[#52525B]">/login → Register → Join with code</span>
        </p>
      </div>
    </main>
  );
}

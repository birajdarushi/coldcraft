import { useState, useEffect } from "react";
import { Users, Search, Plus, Trash2, Edit, Save, Globe, ExternalLink, AlertCircle } from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import { Button, Panel, Field, Input, Textarea, Overline, Tag, Banner, Loading, ErrorBlock, Select } from "../components/ui.jsx";
import { api } from "../lib/api.js";

export default function Network() {
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Search state ("Who at X?")
  const [searchCompany, setSearchCompany] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);

  // Form states
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({
    name: "",
    current_company: "",
    role: "",
    email: "",
    linkedin_url: "",
    x_handle: "",
    relationship: "warm_connection",
    notes: "",
  });

  useEffect(() => {
    fetchContacts();
  }, []);

  async function fetchContacts() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listContacts();
      setContacts(Array.isArray(res) ? res : []);
    } catch (err) {
      setError(err.detail || "Failed to load network contacts.");
    } finally {
      setLoading(false);
    }
  }

  const setVal = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  async function handleSearch(e) {
    e.preventDefault();
    if (!searchCompany.trim()) return;
    setSearching(true);
    setError(null);
    try {
      const res = await api.searchContacts(searchCompany);
      setSearchResults(res);
    } catch (err) {
      setError(err.detail || "Search query failed.");
    } finally {
      setSearching(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    try {
      if (editingId) {
        // Update contact
        const updated = await api.updateContact(editingId, form);
        setContacts((prev) => prev.map((c) => (c.id === editingId ? updated : c)));
        setEditingId(null);
      } else {
        // Create contact
        const created = await api.createContact(form);
        setContacts((prev) => [created, ...prev]);
      }
      resetForm();
    } catch (err) {
      setError(err.detail || "Failed to save contact.");
    }
  }

  async function handleDelete(id) {
    if (!confirm("Are you sure you want to delete this contact?")) return;
    setError(null);
    try {
      await api.deleteContact(id);
      setContacts((prev) => prev.filter((c) => c.id !== id));
      if (editingId === id) resetForm();
    } catch (err) {
      setError(err.detail || "Failed to delete contact.");
    }
  }

  function handleEdit(contact) {
    setEditingId(contact.id);
    setForm({
      name: contact.name || "",
      current_company: contact.current_company || "",
      role: contact.role || "",
      email: contact.email || "",
      linkedin_url: contact.linkedin_url || "",
      x_handle: contact.x_handle || "",
      relationship: contact.relationship || "warm_connection",
      notes: contact.notes || "",
    });
  }

  function resetForm() {
    setEditingId(null);
    setForm({
      name: "",
      current_company: "",
      role: "",
      email: "",
      linkedin_url: "",
      x_handle: "",
      relationship: "warm_connection",
      notes: "",
    });
  }

  return (
    <AppShell title="Network Directory" subtitle="// CRM CONNECTS · WARM OUTREACH ROUTING & REFERRALS">
      <div className="p-4 grid grid-cols-1 lg:grid-cols-3 gap-4 max-w-7xl">
        {/* Left Column: Form & Search */}
        <div className="space-y-4 lg:col-span-1">
          {/* WHO AT X SEARCH CARD */}
          <Panel title="Who at X?" code="company search">
            <form onSubmit={handleSearch} className="space-y-3">
              <p className="font-mono text-[10px] text-muted-foreground">
                Find cold/warm referral paths at a specific target company.
              </p>
              <div className="flex gap-2">
                <Input
                  value={searchCompany}
                  onChange={(e) => setSearchCompany(e.target.value)}
                  placeholder="e.g. Google, Vercel"
                  required
                />
                <Button type="submit" variant="primary" disabled={searching}>
                  <Search className="w-3.5 h-3.5" />
                </Button>
              </div>
            </form>

            {searchResults && (
              <div className="mt-4 border-t border-border pt-3 space-y-2">
                <div className="flex items-center justify-between">
                  <Overline>Search Results</Overline>
                  <button
                    onClick={() => setSearchResults(null)}
                    className="font-mono text-[9px] text-muted-foreground hover:underline"
                  >
                    Clear
                  </button>
                </div>
                {searchResults.length === 0 ? (
                  <div className="text-center font-mono text-[10px] text-muted-foreground py-2 border border-dashed border-border">
                    NO ONE KNOWN AT {searchCompany.toUpperCase()}
                  </div>
                ) : (
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {searchResults.map((c) => (
                      <div key={c.id} className="p-2 border border-border bg-background text-[11px] font-mono">
                        <div className="font-bold text-foreground">{c.name}</div>
                        <div className="text-muted-foreground text-[10px]">{c.role} @ {c.current_company}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Panel>

          {/* ADD / EDIT CONTACT FORM */}
          <Panel title={editingId ? "Edit Contact" : "Add Contact"} code="CRM entry">
            <form onSubmit={handleSubmit} className="space-y-3">
              <Field label="Name" hint="required">
                <Input value={form.name} onChange={setVal("name")} placeholder="John Doe" required />
              </Field>

              <div className="grid grid-cols-2 gap-2">
                <Field label="Company" hint="required">
                  <Input value={form.current_company} onChange={setVal("current_company")} placeholder="Stripe" required />
                </Field>
                <Field label="Role">
                  <Input value={form.role} onChange={setVal("role")} placeholder="Staff Engineer" />
                </Field>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <Field label="Email">
                  <Input type="email" value={form.email} onChange={setVal("email")} placeholder="john@stripe.com" />
                </Field>
                <Field label="Relationship">
                  <Select value={form.relationship} onChange={setVal("relationship")} className="w-full">
                    <option value="warm_connection">Warm Connection</option>
                    <option value="cold_outreach">Cold Outreach</option>
                    <option value="referred_by_other">Referred Path</option>
                    <option value="target_recruiter">Target Recruiter</option>
                  </Select>
                </Field>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <Field label="LinkedIn URL">
                  <Input value={form.linkedin_url} onChange={setVal("linkedin_url")} placeholder="linkedin.com/in/..." />
                </Field>
                <Field label="Twitter / X">
                  <Input value={form.x_handle} onChange={setVal("x_handle")} placeholder="@johndoe" />
                </Field>
              </div>

              <Field label="Relationship Notes">
                <Textarea rows={3} value={form.notes} onChange={setVal("notes")} placeholder="Met at React Conf. Mention GTM optimization projects." />
              </Field>

              {error && <Banner tone="error">{error}</Banner>}

              <div className="flex gap-2">
                <Button type="submit" variant="primary" className="flex-1">
                  <Save className="w-3.5 h-3.5" />
                  {editingId ? "Save Edits" : "Create Contact"}
                </Button>
                {editingId && (
                  <Button type="button" variant="secondary" onClick={resetForm}>
                    Cancel
                  </Button>
                )}
              </div>
            </form>
          </Panel>
        </div>

        {/* Right Column: Contact List */}
        <div className="lg:col-span-2 space-y-4">
          <Panel
            title="Contacts Directory"
            code="warm outreach database"
            right={
              <span className="font-mono text-[10px] text-muted-foreground">
                TOTAL: {contacts.length}
              </span>
            }
          >
            {loading ? (
              <Loading label="LOADING CONTACTS..." />
            ) : contacts.length === 0 ? (
              <div className="border border-dashed border-border p-12 text-center text-muted-foreground font-mono text-[12px]">
                NO CONTACTS SAVED. ADD A CONTACT ENTRY ON THE LEFT.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {contacts.map((c) => (
                  <div
                    key={c.id}
                    className="border border-border bg-surface p-3.5 flex flex-col justify-between space-y-3 rounded-sm"
                  >
                    <div>
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-sans font-bold text-[14px] text-foreground leading-none">
                            {c.name}
                          </h4>
                          <span className="font-mono text-[10px] text-muted-foreground mt-1 block">
                            {c.role || "Professional"} @ {c.current_company}
                          </span>
                        </div>
                        <Tag className="border-border/65">{c.relationship?.replace("_", " ")}</Tag>
                      </div>

                      {c.notes && (
                        <p className="font-sans text-[11px] text-muted-foreground/90 mt-2.5 bg-background border border-border/40 p-2 rounded-sm select-text">
                          {c.notes}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-border/30">
                      <div className="flex gap-2 text-muted-foreground">
                        {c.email && (
                          <a href={`mailto:${c.email}`} className="hover:text-foreground">
                            <Globe className="w-3.5 h-3.5" title={c.email} />
                          </a>
                        )}
                        {c.linkedin_url && (
                          <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer" className="hover:text-foreground">
                            <ExternalLink className="w-3.5 h-3.5" title="LinkedIn Profile" />
                          </a>
                        )}
                        {c.x_handle && (
                          <a href={`https://x.com/${c.x_handle.replace("@", "")}`} target="_blank" rel="noopener noreferrer" className="hover:text-foreground">
                            <ExternalLink className="w-3.5 h-3.5" title="Twitter / X Profile" />
                          </a>
                        )}
                      </div>

                      <div className="flex gap-1.5">
                        <button
                          onClick={() => handleEdit(c)}
                          className="p-1 border border-border hover:bg-muted text-muted-foreground hover:text-foreground"
                          title="Edit"
                        >
                          <Edit className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => handleDelete(c.id)}
                          className="p-1 border border-red-500/30 hover:bg-red-500/10 text-red-500/80 hover:text-red-500"
                          title="Delete"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>
    </AppShell>
  );
}

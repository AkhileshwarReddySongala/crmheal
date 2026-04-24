import { UploadCloud } from "lucide-react";

export function FileUpload({ onFile, isLoading }) {
  return (
    <section className="upload-shell">
      <div className="upload-zone">
        <UploadCloud size={42} />
        <h1>Drop your dirty CRM</h1>
        <p>CRM Heal autonomously deduplicates, enriches from the web, verifies contacts via voice, and persists the result.</p>
        <label className="primary-button file-button">
          {isLoading ? "Scanning..." : "Choose CSV"}
          <input
            type="file"
            accept=".csv"
            disabled={isLoading}
            onChange={(event) => event.target.files?.[0] && onFile(event.target.files[0])}
          />
        </label>
      </div>
    </section>
  );
}

export class DataverseClient {
  constructor(baseUrl = window.location.origin) { this.baseUrl = baseUrl.replace(/\/$/, ""); }
  async request(path, options = {}) {
    const response = await fetch(`${this.baseUrl}/api/data/v9.2/${path}`, {
      credentials: "same-origin",
      headers: { "Accept": "application/json", "Content-Type": "application/json", ...(options.headers || {}) },
      ...options
    });
    if (!response.ok) throw new Error(`Dataverse request failed: ${response.status}`);
    return response.status === 204 ? null : response.json();
  }
  create(entitySet, record) { return this.request(entitySet, { method: "POST", body: JSON.stringify(record) }); }
  update(entitySet, id, patch) { return this.request(`${entitySet}(${id})`, { method: "PATCH", body: JSON.stringify(patch) }); }
  list(entitySet, query = "") { return this.request(`${entitySet}${query}`); }
}

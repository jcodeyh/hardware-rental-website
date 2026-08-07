
import URLs from "../url";

class AuthService {
  constructor() {
    // Vite inlines VITE_* at build time; falls back to the local Flask
    // server so `npm run dev` keeps working with no extra setup.
    this.baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    this.headers = { "Content-Type": "application/json" };
  }

  async login(requestObject) {
    let url = this.baseUrl + URLs.login;
    let response = await fetch(url, {
      method: "POST",
      headers: this.headers,
      // The API is a different origin, and fetch defaults to
      // credentials: "same-origin" -- without this the browser silently
      // discards the session cookie the server sets here.
      credentials: "include",
      body: JSON.stringify(requestObject),
    });
    const data = await response.json();
    return data
  }

  async signup(requestObject) {
    let url = this.baseUrl + URLs.signUp;
    let response = await fetch(url, {
      method: "POST",
      headers: this.headers,
      credentials: "include",
      body: JSON.stringify(requestObject),
    });
    const data = await response.json();
    return data;
  }

  // ── Auth ──────────────────────────────────────────────────────────────
  async logout() {
    let url = this.baseUrl + URLs.logout;
    let response = await fetch(url, {
      method: "POST",
      headers: this.headers,
      credentials: "include",
    });
    return response.status; // 204 on success
  }

  // ── Projects ──────────────────────────────────────────────────────────

  /** GET /get_project_info?projectId=<id> */
  async getProjectInfo(projectId) {
    let url = this.baseUrl + URLs.getProjectInfo + `?projectId=${encodeURIComponent(projectId)}`;
    let response = await fetch(url, {
      method: "GET",
      headers: this.headers,
      credentials: "include",
    });
    const data = await response.json();
    return data;
  }

  /** POST /create_project  — body: { projectId, projectName, description, hwSets } */
  async createProject(requestObject) {
    let url = this.baseUrl + URLs.createProject;
    let response = await fetch(url, {
      method: "POST",
      headers: this.headers,
      credentials: "include",
      body: JSON.stringify(requestObject),
    });
    const data = await response.json();
    return data;
  }

  /** POST /join_project  — body: { projectId } */
  async joinProject(requestObject) {
    let url = this.baseUrl + URLs.joinProject;
    let response = await fetch(url, {
      method: "POST",
      headers: this.headers,
      credentials: "include",
      body: JSON.stringify(requestObject),
    });
    const data = await response.json();
    return data;
  }

  /** GET /get_user_projects_list */
  async getUserProjects() {
    let url = this.baseUrl + URLs.getUserProjects;
    let response = await fetch(url, {
      method: "GET",
      headers: this.headers,
      credentials: "include",
    });
    const data = await response.json();
    return data;
  }

  // ── Hardware ──────────────────────────────────────────────────────────

  /** GET /get_all_hw_names */
  async getAllHwNames() {
    let url = this.baseUrl + URLs.getAllHwNames;
    let response = await fetch(url, {
      method: "GET",
      credentials: "include",
    });
    const data = await response.json();
    return data;
  }

  /** GET /api/inventory */
  async getInventory() {
    let url = this.baseUrl + URLs.getInventory;
    let response = await fetch(url, {
      method: "GET",
      credentials: "include",
    });
    const data = await response.json();
    return data;
  }

  /** POST /check_out  — body: { projectId, hwSetName, qty } */
  async checkOut(requestObject) {
    let url = this.baseUrl + URLs.checkOut;
    let response = await fetch(url, {
      method: "POST",
      headers: this.headers,
      credentials: "include",
      body: JSON.stringify(requestObject),
    });
    const data = await response.json();
    return data;
  }

  /** POST /check_in  — body: { projectId, hwSetName, qty } */
  async checkIn(requestObject) {
    let url = this.baseUrl + URLs.checkIn;
    let response = await fetch(url, {
      method: "POST",
      headers: this.headers,
      credentials: "include",
      body: JSON.stringify(requestObject),
    });
    const data = await response.json();
    return data;
  }
}

export default new AuthService();


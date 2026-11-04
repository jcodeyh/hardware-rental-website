import URLs from "../url";

class AuthService {
  constructor() {
    this.baseUrl = import.meta.env.VITE_API_BASE_URL || "/api/app";
  }

  async send(path, method = "GET", body) {
    const options = { method, credentials: "include" };
    if (body !== undefined) {
      options.headers = { "Content-Type": "application/json" };
      options.body = JSON.stringify(body);
    }
    const response = await fetch(this.baseUrl + path, options);
    let data;
    try {
      data = await response.json();
    } catch {
      data = {};
    }
    if (!response.ok && !data.error) {
      data.error = data.message || `Request failed with status ${response.status}`;
    }
    return data;
  }

  login(requestObject) {
    return this.send(URLs.login, "POST", requestObject);
  }

  signup(requestObject) {
    return this.send(URLs.signUp, "POST", requestObject);
  }

  async logout() {
    const response = await fetch(this.baseUrl + URLs.logout, {
      method: "POST",
      credentials: "include",
    });
    return response.status;
  }

  getProjectInfo(projectId) {
    return this.send(`${URLs.projects}/${encodeURIComponent(projectId)}`);
  }

  createProject(requestObject) {
    return this.send(URLs.projects, "POST", requestObject);
  }

  joinProject(requestObject) {
    return this.send(URLs.joinProject, "POST", requestObject);
  }

  getUserProjects() {
    return this.send(URLs.getUserProjects);
  }

  getInventory() {
    return this.send(URLs.projects);
  }

  getHardware() {
    return this.send(`${URLs.hardware}?size=100`);
  }

  checkOut(requestObject) {
    return this.send(URLs.checkOut, "POST", requestObject);
  }

  checkIn(requestObject) {
    return this.send(URLs.checkIn, "POST", requestObject);
  }
}

export default new AuthService();

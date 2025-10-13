(function () {
  if (!window.Vue || !window.Vuetify) {
    console.error("Vue.js and Vuetify are required");
    return;
  }

  const { createApp, ref, watch, onMounted, nextTick } = window.Vue;
  const { createVuetify } = window.Vuetify;

  const vuetify = createVuetify({
    theme: {
      defaultTheme: "light",
      themes: {
        light: {
          dark: false,
          colors: {
            primary: "#667eea",
            secondary: "#764ba2",
            accent: "#82B1FF",
            error: "#FF5252",
            info: "#2196F3",
            success: "#4CAF50",
            warning: "#FB8C00",
            background: "#FFFFFF",
          },
        },
        dark: {
          dark: true,
          colors: {
            primary: "#667eea",
            secondary: "#764ba2",
            accent: "#FF4081",
            error: "#FF5252",
            info: "#2196F3",
            success: "#4CAF50",
            warning: "#FB8C00",
            background: "#121212",
          },
        },
      },
    },
  });

  const app = createApp({
    setup() {
      // State variables
      const currentView = ref("login");
      const loginValid = ref(false);
      const registerValid = ref(false);
      const loginError = ref("");
      const registerError = ref("");
      const loading = ref(false);
      const showPassword = ref(false);
      const showConfirmPassword = ref(false);
      const isDark = ref(false);

      const loginData = ref({
        email: "",
        password: "",
        rememberMe: false
      });

      const registerData = ref({
        firstName: "",
        lastName: "",
        email: "",
        password: "",
        confirmPassword: "",
        acceptTerms: false,
      });

      const user = ref(null);
      const snackbar = ref({
        show: false,
        message: "",
        color: "",
        timeout: 3000
      });

      const stats = ref({
        totalDocuments: '12.5K',
        successRate: 98.7,
        avgProcessingTime: 2.3,
        activeUsers: '1.2K'
      });

      // Validation rules
      const emailRules = [
        (v) => !!v || "Email is required",
        (v) => /.+@.+\..+/.test(v) || "Email must be valid",
      ];

      const passwordRules = [
        (v) => !!v || "Password is required",
        (v) => v.length >= 8 || "Password must be at least 8 characters long",
        (v) => /[A-Z]/.test(v) || "Password must contain at least one uppercase letter",
        (v) => /[a-z]/.test(v) || "Password must contain at least one lowercase letter",
        (v) => /[0-9]/.test(v) || "Password must contain at least one number",
      ];

      const nameRules = [
        (v) => !!v || "Name is required",
        (v) => v.length >= 2 || "Name must be at least 2 characters long",
        (v) => /^[a-zA-Z\s-]+$/.test(v) || "Name can only contain letters, spaces, or hyphens",
      ];

      const confirmPasswordRules = [
        (v) => !!v || "Confirm password is required",
        (v) => v === registerData.value.password || "Passwords must match",
      ];

      const termsRules = [(v) => !!v || "You must agree to the terms"];

      let chatApp = null;

      // Lifecycle hooks
      onMounted(() => {
        if (localStorage.getItem("rememberedEmail")) {
          loginData.value.email = localStorage.getItem("rememberedEmail");
          loginData.value.rememberMe = true;
        }
        checkAuth();
      });

      // Watchers
      watch(
        () => currentView.value,
        async (newVal) => {
          if (newVal === "login" && !user.value) {
            currentView.value = "login";
            showNotification("Please log in to access the dashboard", "error");
          } else if (newVal === "chat") {
            await nextTick();
            mountChatApp();
          }
        },
        { immediate: true }
      );

      // Authentication functions
      async function checkAuth() {
        try {
          const response = await fetch("/auth/protected", {
            credentials: "include",
            headers: { "Content-Type": "application/json" },
          });

          if (response.status === 401) {
            user.value = null;
            currentView.value = "login";
            return;
          }

          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }

          const data = await response.json();
          if (data.success && data.user) {
            user.value = data.user;
            localStorage.setItem("user_id", data.user.id);
            localStorage.setItem("user_data", JSON.stringify(data.user));
            currentView.value = "dashboard";
          } else {
            user.value = null;
            currentView.value = "login";
          }
        } catch (error) {
          console.error("Auth check failed:", error);
          user.value = null;
          currentView.value = "login";
          showNotification("Failed to verify session. Please log in.", "error");
        }
      }

      async function login() {
        loading.value = true;
        loginError.value = "";

        try {
          const response = await fetch("/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({
              email: loginData.value.email,
              password: loginData.value.password,
            }),
          });

          const data = await response.json();

          if (response.status === 401) {
            throw new Error("Invalid credentials");
          }

          if (!response.ok) {
            throw new Error(data.message || "Login failed");
          }

          user.value = data.user;
          localStorage.setItem("user_id", data.user.id);
          localStorage.setItem("user_data", JSON.stringify(data.user));
          localStorage.setItem("userInfo", JSON.stringify(data.user)); // For admin feature compatibility
          currentView.value = "dashboard";

          if (loginData.value.rememberMe) {
            localStorage.setItem("rememberedEmail", loginData.value.email);
          } else {
            localStorage.removeItem("rememberedEmail");
          }

          showNotification("Logged in successfully", "success");
        } catch (error) {
          loginError.value = error.message;
          showNotification(error.message, "error");
        } finally {
          loading.value = false;
        }
      }

      async function register() {
        loading.value = true;
        registerError.value = "";

        try {
          const response = await fetch("/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({
              firstName: registerData.value.firstName,
              lastName: registerData.value.lastName,
              email: registerData.value.email,
              password: registerData.value.password,
            }),
          });

          const data = await response.json();

          if (response.status === 401) {
            throw new Error("Unauthorized registration attempt");
          }

          if (!response.ok) {
            throw new Error(data.message || "Registration failed");
          }

          user.value = data.user;
          localStorage.setItem("user_id", data.user.id);
          localStorage.setItem("user_data", JSON.stringify(data.user));
          localStorage.setItem("userInfo", JSON.stringify(data.user)); // For admin feature compatibility
          currentView.value = "dashboard";

          showNotification("Registered successfully", "success");
        } catch (error) {
          registerError.value = error.message;
          showNotification(error.message, "error");
        } finally {
          loading.value = false;
        }
      }

      async function logout() {
        try {
          const response = await fetch("/auth/logout", {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
          });

          if (!response.ok) {
            throw new Error("Logout failed");
          }

          user.value = null;
          currentView.value = "login";
          localStorage.removeItem("rememberedEmail");
          localStorage.removeItem("user_id");
          localStorage.removeItem("user_data");

          if (chatApp) {
            chatApp.unmount();
            chatApp = null;
          }

          showNotification("Logged out successfully", "success");
        } catch (error) {
          showNotification("Logout failed", "error");
        }
      }

      // Chat app mounting
      function mountChatApp() {
        if (!chatApp) {
          try {
            chatApp = window.createChatApp && window.createChatApp();
            if (!chatApp) {
              console.error("createChatApp is undefined or returned null");
              return;
            }
            chatApp.use(vuetify).mount("#chat-app");
          } catch (error) {
            console.error("Failed to mount chat app:", error);
          }
        }
      }

      // Utility functions
      function showNotification(message, color = 'success') {
        snackbar.value = {
          show: true,
          message,
          color,
          timeout: 3000
        };
      }

      function toggleTheme() {
        isDark.value = !isDark.value;
        document.body.classList.toggle('dark-mode', isDark.value);
        showNotification(`Switched to ${isDark.value ? 'dark' : 'light'} mode`, 'info');
      }

      // Navigation functions
      function navigateToChat() {
        showNotification('Launching AI Help Bot...', 'info');
        setTimeout(() => {
          currentView.value = "chat";
        }, 1000);
      }

      function navigateToDocClass() {
        showNotification('Opening Document Classification...', 'info');
        setTimeout(() => {
          currentView.value = "chat"; // For now, redirect to chat
        }, 1000);
      }

      function navigateToGuarantee() {
        showNotification('Loading Guarantee Vetting...', 'info');
        setTimeout(() => {
          currentView.value = "chat"; // For now, redirect to chat
        }, 1000);
      }

      function navigateToAnalytics() {
        showNotification('Opening Analytics Dashboard...', 'info');
        setTimeout(() => {
          showNotification('Analytics feature coming soon!', 'warning');
        }, 1000);
      }

      function navigateToAPI() {
        showNotification('Accessing API Management...', 'info');
        setTimeout(() => {
          showNotification('API Management feature coming soon!', 'warning');
        }, 1000);
      }

      function navigateToSettings() {
        showNotification('Opening Settings...', 'info');
        setTimeout(() => {
          showNotification('Settings feature coming soon!', 'warning');
        }, 1000);
      }

      function backToDashboard() {
        if (chatApp) {
          chatApp.unmount();
          chatApp = null;
        }
        currentView.value = "dashboard";
      }

      // Return all reactive data and functions
      return {
        // State
        currentView,
        loginValid,
        registerValid,
        loginError,
        registerError,
        loading,
        showPassword,
        showConfirmPassword,
        isDark,
        loginData,
        registerData,
        user,
        snackbar,
        stats,

        // Validation rules
        emailRules,
        passwordRules,
        nameRules,
        confirmPasswordRules,
        termsRules,

        // Authentication functions
        login,
        register,
        logout,

        // Utility functions
        toggleTheme,
        showNotification,

        // Navigation functions
        navigateToChat,
        navigateToDocClass,
        navigateToGuarantee,
        navigateToAnalytics,
        navigateToAPI,
        navigateToSettings,
        backToDashboard,
      };
    },
  });

  app.use(vuetify);
  app.mount("#app");
})();
/**
 * Keeps the logged-in account in sessionStorage (it is cleared when the tab is
 * closed). Load this file before the script of any page that needs the login.
 */
const QuaseflixSession = (() => {
  const TOKEN_KEY = "quaseflix_token";
  const ACCOUNT_KEY = "quaseflix_account";

  const save = (token, account) => {
    sessionStorage.removeItem("quaseflix_profile");
    sessionStorage.setItem(TOKEN_KEY, token);
    sessionStorage.setItem(ACCOUNT_KEY, JSON.stringify(account));
  };

  const clear = () => {
    sessionStorage.removeItem("quaseflix_profile");
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(ACCOUNT_KEY);
  };

  const getToken = () => sessionStorage.getItem(TOKEN_KEY);

  const getAccount = () => {
    try {
      return JSON.parse(sessionStorage.getItem(ACCOUNT_KEY));
    } catch {
      return null;
    }
  };

  const setProfile = (profile) => {
    if (profile) sessionStorage.setItem("quaseflix_profile", JSON.stringify(profile));
    else sessionStorage.removeItem("quaseflix_profile");
  };

  return { save, clear, getToken, getAccount, setProfile };
})();

import { authApi } from '../api/auth';

export function Login() {
  const handleLogin = () => {
    window.location.href = authApi.getMicrosoftAuthUrl();
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black px-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <img
            src="/kingcap-logo.png"
            alt="King Cap"
            className="h-16 w-auto mx-auto mb-4"
          />
          <h1 className="text-2xl font-bold text-gray-100">King Cap HQ</h1>
          <p className="text-gray-400 mt-2">Sign in with your work account</p>
        </div>

        <div className="bg-gray-900 rounded-xl shadow-lg border border-gray-800 p-6">
          <button
            onClick={handleLogin}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition-colors border border-gray-700"
          >
            <svg className="w-5 h-5" viewBox="0 0 21 21">
              <rect x="1" y="1" width="9" height="9" fill="#F25022" />
              <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
              <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
              <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
            </svg>
            <span className="font-medium">Sign in with Microsoft</span>
          </button>
        </div>

        <p className="text-center text-sm text-gray-500 mt-6">
          Contact your administrator if you need access
        </p>
      </div>
    </div>
  );
}

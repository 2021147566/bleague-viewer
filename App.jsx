import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppShell from "./AppShell.jsx";
import RosterPage from "./pages/RosterPage.jsx";
import CalcPage from "./pages/CalcPage.jsx";
import { RosterConferenceProvider } from "./RosterConferenceContext.jsx";

const basename = import.meta.env.BASE_URL.replace(/\/$/, "");

export default function App() {
  return (
    <RosterConferenceProvider>
      <BrowserRouter basename={basename || undefined}>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<RosterPage />} />
            <Route path="calc" element={<CalcPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </RosterConferenceProvider>
  );
}

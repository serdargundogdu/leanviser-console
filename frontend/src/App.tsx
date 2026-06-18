import { Navigate, Route, Routes } from "react-router-dom";
import FinancePage from "./pages/FinancePage";

// İlk route finance (/finance). Kök adres oraya yönlendirir.
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/finance" replace />} />
      <Route path="/finance" element={<FinancePage />} />
    </Routes>
  );
}

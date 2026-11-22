import { Outlet, Route, Routes } from "react-router-dom";
import { FileQuestion } from "lucide-react";
import Layout from "./components/Layout";
import { EmptyState } from "./components/ui";
import { AuthProvider, RedirectIfAuthed, RequireAdmin, RequireAuth } from "./lib/auth";
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";
import Dashboard from "./pages/Dashboard";
import Contracts from "./pages/Contracts";
import Upload from "./pages/Upload";
import ContractDetail from "./pages/ContractDetail";
import Obligations from "./pages/Obligations";
import Templates from "./pages/Templates";
import Policies from "./pages/Policies";
import Settings from "./pages/Settings";
import Profile from "./pages/Profile";
import AdminOverview from "./pages/admin/AdminOverview";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminContracts from "./pages/admin/AdminContracts";

function AppShell() {
  return (
    <RequireAuth>
      <Layout>
        <Outlet />
      </Layout>
    </RequireAuth>
  );
}

function AdminOnly() {
  return (
    <RequireAdmin>
      <Outlet />
    </RequireAdmin>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* public */}
        <Route path="/login" element={<RedirectIfAuthed><Login /></RedirectIfAuthed>} />
        <Route path="/register" element={<RedirectIfAuthed><Register /></RedirectIfAuthed>} />

        {/* signed-in users */}
        <Route element={<AppShell />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/contracts" element={<Contracts />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/contracts/:id" element={<ContractDetail />} />
          <Route path="/obligations" element={<Obligations />} />
          <Route path="/templates" element={<Templates />} />
          <Route path="/policies" element={<Policies />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/profile" element={<Profile />} />

          {/* admins only */}
          <Route element={<AdminOnly />}>
            <Route path="/admin" element={<AdminOverview />} />
            <Route path="/admin/users" element={<AdminUsers />} />
            <Route path="/admin/contracts" element={<AdminContracts />} />
          </Route>

          <Route path="*" element={<EmptyState icon={FileQuestion} title="Page not found" />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}

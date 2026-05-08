import { create } from "zustand";

export type Rol = "admin" | "especialista";

interface UsuarioState {
  nombre: string;
  correo: string;
  rol: Rol | null;
  setUsuario: (nombre: string, correo: string, rol: Rol) => void;
  clear: () => void;
}

export const useUsuarioStore = create<UsuarioState>((set) => ({
  nombre: "",
  correo: "",
  rol: null,
  setUsuario: (nombre, correo, rol) => set({ nombre, correo, rol }),
  clear: () => set({ nombre: "", correo: "", rol: null }),
}));

interface NotifState {
  mensaje: string | null;
  tipo: "success" | "error" | "info";
  mostrar: (msg: string, tipo?: "success" | "error" | "info") => void;
  limpiar: () => void;
}

export const useNotifStore = create<NotifState>((set) => ({
  mensaje: null,
  tipo: "info",
  mostrar: (mensaje, tipo = "info") => set({ mensaje, tipo }),
  limpiar: () => set({ mensaje: null }),
}));

import { useState, useEffect } from "react";
import { Table, Button, Modal, Form, Input, Select, Tag, Popconfirm, Empty } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import api from "../services/apiClient";
import { useNotifStore } from "../store/store";

type Cliente = { id: string; nombre: string };
type Usuario = { id: string; correo: string; nombre: string; rol: string; activo: boolean; clientes: Cliente[] };

export function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Usuario | null>(null);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const { mostrar } = useNotifStore();

  useEffect(() => {
    cargar();
    api.get("/clientes").then((r) => setClientes(r.data)).catch(() => {});
  }, []);

  const cargar = async () => {
    setLoading(true);
    try {
      const r = await api.get("/usuarios");
      setUsuarios(r.data);
    } finally {
      setLoading(false);
    }
  };

  const abrirModal = (usuario?: Usuario) => {
    setEditando(usuario ?? null);
    form.setFieldsValue(
      usuario
        ? { ...usuario, cliente_ids: usuario.clientes.map((c) => c.id) }
        : { rol: "especialista", cliente_ids: [] }
    );
    setModalOpen(true);
  };

  const guardar = async (values: Record<string, unknown>) => {
    try {
      if (editando) {
        await api.put(`/usuarios/${editando.id}`, values);
        mostrar("Usuario actualizado correctamente", "success");
      } else {
        await api.post("/usuarios", values);
        mostrar("Usuario creado correctamente", "success");
      }
      setModalOpen(false);
      await cargar();
    } catch {
      mostrar("Error al guardar el usuario", "error");
    }
  };

  const eliminar = async (id: string) => {
    try {
      await api.delete(`/usuarios/${id}`);
      mostrar("Usuario eliminado", "info");
      await cargar();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      mostrar(msg ?? "Error al eliminar el usuario", "error");
    }
  };

  const columns: ColumnsType<Usuario> = [
    { title: "Nombre", dataIndex: "nombre", key: "nombre", sorter: (a, b) => a.nombre.localeCompare(b.nombre) },
    { title: "Correo", dataIndex: "correo", key: "correo" },
    { title: "Rol", dataIndex: "rol", key: "rol",
      render: (v) => <Tag color={v === "admin" ? "#1987af" : "#64748b"}>{v}</Tag> },
    { title: "Clientes asignados", dataIndex: "clientes", key: "clientes",
      render: (cls: Cliente[]) => cls.length > 0
        ? cls.map(c => <Tag key={c.id} style={{ marginBottom: 2 }}>{c.nombre}</Tag>)
        : <span style={{ color: "#94a3b8" }}>Sin asignar</span> },
    { title: "", key: "acc", width: 100,
      render: (_, r) => (
        <div style={{ display: "flex", gap: 8 }}>
          <Button size="small" icon={<EditOutlined />} onClick={() => abrirModal(r)} />
          <Popconfirm
            title="¿Eliminar este usuario?"
            okText="Sí, eliminar"
            cancelText="Cancelar"
            onConfirm={() => eliminar(r.id)}
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </div>
      ) },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Gestión de usuarios</h1>
        <p>Administra los usuarios del sistema y sus clientes asignados</p>
      </div>

      <div style={{ marginBottom: 16 }}>
        <button className="btn-primary" onClick={() => abrirModal()}>
          <PlusOutlined /> Nuevo usuario
        </button>
      </div>

      <div className="card">
        <Table
          columns={columns}
          dataSource={usuarios}
          rowKey="id"
          loading={loading}
          locale={{ emptyText: <Empty description="No hay usuarios registrados" /> }}
          pagination={{ pageSize: 15 }}
        />
      </div>

      <Modal
        title={editando ? "Editar usuario" : "Nuevo usuario"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={null}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={guardar} style={{ marginTop: 16 }}>
          {!editando && (
            <Form.Item name="correo" label="Correo corporativo" rules={[{ required: true, type: "email" }]}>
              <Input placeholder="usuario@empresa.com" />
            </Form.Item>
          )}
          <Form.Item name="nombre" label="Nombre completo" rules={[{ required: true }]}>
            <Input placeholder="Nombre del usuario" />
          </Form.Item>
          <Form.Item name="rol" label="Rol" rules={[{ required: true }]}>
            <Select options={[{ value: "especialista", label: "Especialista" }, { value: "admin", label: "Administrador" }]} />
          </Form.Item>
          <Form.Item name="cliente_ids" label="Clientes asignados">
            <Select
              mode="multiple"
              placeholder="Selecciona los clientes"
              options={clientes.map((c) => ({ value: c.id, label: c.nombre }))}
            />
          </Form.Item>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button type="primary" htmlType="submit">Guardar</Button>
          </div>
        </Form>
      </Modal>
    </div>
  );
}

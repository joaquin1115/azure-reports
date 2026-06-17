import { useState, useEffect } from "react";
import { Table, Button, Modal, Form, Input, Popconfirm, Tag, Empty, Space } from "antd";
import { PlusOutlined, EditOutlined, PauseCircleOutlined, MinusCircleOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import api from "../services/apiClient";
import { useNotifStore } from "../store/store";

type Tenant = { id?: string; tenant_id_azure: string; nombre: string };
type Cliente = { id: string; nombre: string; activo: boolean; tenants: Tenant[] };

export function ClientesPage() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Cliente | null>(null);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const { mostrar } = useNotifStore();

  useEffect(() => { cargar(); }, []);

  const cargar = async () => {
    setLoading(true);
    try {
      const r = await api.get("/clientes");
      setClientes(r.data);
    } finally {
      setLoading(false);
    }
  };

  const abrirModal = (cliente?: Cliente) => {
    setEditando(cliente ?? null);
    form.setFieldsValue(
      cliente
        ? { nombre: cliente.nombre, tenants: cliente.tenants }
        : { nombre: "", tenants: [{ tenant_id_azure: "", nombre: "" }] }
    );
    setModalOpen(true);
  };

  const guardar = async (values: { nombre: string; tenants: Tenant[] }) => {
    try {
      if (editando) {
        await api.put(`/clientes/${editando.id}`, values);
        mostrar("Cliente actualizado correctamente", "success");
      } else {
        await api.post("/clientes", values);
        mostrar("Cliente creado correctamente", "success");
      }
      setModalOpen(false);
      await cargar();
    } catch {
      mostrar("Error al guardar el cliente", "error");
    }
  };

  const desactivar = async (id: string) => {
    try {
      await api.patch(`/clientes/${id}/desactivar`);
      mostrar("Cliente desactivado", "info");
      await cargar();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      mostrar(msg ?? "Error al desactivar el cliente", "error");
    }
  };

  const columns: ColumnsType<Cliente> = [
    { title: "Nombre", dataIndex: "nombre", key: "nombre", sorter: (a, b) => a.nombre.localeCompare(b.nombre) },
    { title: "Tenants de Azure", dataIndex: "tenants", key: "tenants",
      render: (tenants: Tenant[]) =>
        tenants.map((t) => (
          <Tag key={t.tenant_id_azure} color="#1987af" style={{ marginBottom: 2, fontFamily: "monospace", fontSize: 11 }}>
            {t.nombre} ({t.tenant_id_azure.slice(0, 8)}…)
          </Tag>
        ))
    },
    { title: "Estado", dataIndex: "activo", key: "activo",
      render: (v) => v
        ? <span className="badge-estado badge-completado">Activo</span>
        : <span className="badge-estado badge-error">Inactivo</span> },
    { title: "", key: "acc", width: 100,
      render: (_, r) => (
        <div style={{ display: "flex", gap: 8 }}>
          <Button size="small" icon={<EditOutlined />} onClick={() => abrirModal(r)} />
          {r.activo && (
            <Popconfirm
              title="¿Desactivar este cliente?"
              description="El cliente quedará inactivo, pero se conservará la trazabilidad de sus reportes."
              okText="Sí, desactivar"
              cancelText="Cancelar"
              onConfirm={() => desactivar(r.id)}
            >
              <Button size="small" danger icon={<PauseCircleOutlined />} />
            </Popconfirm>
          )}
        </div>
      ) },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Gestión de clientes</h1>
        <p>Administra los clientes de G&S y sus tenants de Azure</p>
      </div>

      <div style={{ marginBottom: 16 }}>
        <button className="btn-primary" onClick={() => abrirModal()}>
          <PlusOutlined /> Nuevo cliente
        </button>
      </div>

      <div className="card">
        <Table
          columns={columns}
          dataSource={clientes}
          rowKey="id"
          loading={loading}
          locale={{ emptyText: <Empty description="No hay clientes registrados" /> }}
          pagination={{ pageSize: 15 }}
        />
      </div>

      <Modal
        title={editando ? "Editar cliente" : "Nuevo cliente"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={null}
        destroyOnClose
        width={560}
      >
        <Form form={form} layout="vertical" onFinish={guardar} style={{ marginTop: 16 }}>
          <Form.Item name="nombre" label="Nombre del cliente" rules={[{ required: true }]}>
            <Input placeholder="Nombre de la empresa" />
          </Form.Item>

          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: "#1e293b" }}>
            Tenants de Azure
          </div>

          <Form.List name="tenants">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...rest }) => (
                  <div key={key} style={{ display: "flex", gap: 10, alignItems: "flex-start", marginBottom: 8 }}>
                    <Form.Item
                      {...rest}
                      name={[name, "nombre"]}
                      rules={[{ required: true, message: "Nombre requerido" }]}
                      style={{ flex: 1, marginBottom: 0 }}
                    >
                      <Input placeholder="Nombre del tenant" />
                    </Form.Item>
                    <Form.Item
                      {...rest}
                      name={[name, "tenant_id_azure"]}
                      rules={[{ required: true, message: "Tenant ID requerido" }]}
                      style={{ flex: 1.5, marginBottom: 0 }}
                    >
                      <Input placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" style={{ fontFamily: "monospace", fontSize: 12 }} />
                    </Form.Item>
                    {fields.length > 1 && (
                      <Button
                        type="text"
                        danger
                        icon={<MinusCircleOutlined />}
                        onClick={() => remove(name)}
                        style={{ marginTop: 4 }}
                      />
                    )}
                  </div>
                ))}
                <Button
                  type="dashed"
                  onClick={() => add({ nombre: "", tenant_id_azure: "" })}
                  icon={<PlusOutlined />}
                  style={{ width: "100%", marginBottom: 16 }}
                >
                  Agregar tenant
                </Button>
              </>
            )}
          </Form.List>

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button type="primary" htmlType="submit">Guardar</Button>
          </div>
        </Form>
      </Modal>
    </div>
  );
}

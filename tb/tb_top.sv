// tb_top.sv — simulation top level: a core wired to sim_mem
//
// cocotb drives clk/rst and reads the trace_* signals from here.
// Builds the pipelined core by default; define SINGLE_CYCLE for the
// single-cycle one. Both cores have the same ports and the same trace.

`ifdef SINGLE_CYCLE
  `define CORE_MODULE core_single
  `define MEM_SYNC_READ 1'b0
`else
  `define CORE_MODULE core
  `define MEM_SYNC_READ 1'b1
`endif

module tb_top #(
    parameter logic [31:0] RESET_PC = 32'h0000_0000   // riscv-tests use 0x8000_0000
) (
    input  logic        clk,
    input  logic        rst,

    output logic        trace_valid,
    output logic [31:0] trace_pc,
    output logic [31:0] trace_instr,
    output logic        trace_rd_we,
    output logic [4:0]  trace_rd,
    output logic [31:0] trace_rd_wdata,
    output logic        trace_illegal,
    output logic        trace_trap,
    output logic [31:0] trace_cause,
    output logic [31:0] trace_mem_addr,
    output logic [3:0]  trace_mem_wstrb,
    output logic [31:0] trace_mem_wdata
);

    logic [31:0] imem_addr, imem_rdata, dmem_addr, dmem_wdata, dmem_rdata;
    logic [3:0]  dmem_wstrb;

    `CORE_MODULE #(.RESET_PC(RESET_PC)) u_core (
        .clk             (clk),
        .rst             (rst),
        .imem_addr       (imem_addr),
        .imem_rdata      (imem_rdata),
        .dmem_addr       (dmem_addr),
        .dmem_wdata      (dmem_wdata),
        .dmem_wstrb      (dmem_wstrb),
        .dmem_rdata      (dmem_rdata),
        .trace_valid     (trace_valid),
        .trace_pc        (trace_pc),
        .trace_instr     (trace_instr),
        .trace_rd_we     (trace_rd_we),
        .trace_rd        (trace_rd),
        .trace_rd_wdata  (trace_rd_wdata),
        .trace_illegal   (trace_illegal),
        .trace_trap      (trace_trap),
        .trace_cause     (trace_cause),
        .trace_mem_addr  (trace_mem_addr),
        .trace_mem_wstrb (trace_mem_wstrb),
        .trace_mem_wdata (trace_mem_wdata)
    );

    sim_mem #(.SYNC_READ(`MEM_SYNC_READ)) u_mem (
        .clk    (clk),
        .iaddr  (imem_addr),
        .irdata (imem_rdata),
        .daddr  (dmem_addr),
        .dwdata (dmem_wdata),
        .dwstrb (dmem_wstrb),
        .drdata (dmem_rdata)
    );

endmodule

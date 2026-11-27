"""MCP dữ liệu công khai: `python -m investment_agent.mcp_server` serves public market data to Claude over stdio, read-only.

Only investment_agent.public_tools is wired in; no personal record is reachable from here (a test checks the imports).
"""

from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from investment_agent.public_tools import PublicData, default_data_dir, vn_times

INSTRUCTIONS = (
    "Dữ liệu thị trường công khai của sàn HOSE từ kho trên máy (VNDirect, HOSE, nguồn vĩ mô công khai). Số giữ nguyên như trong kho, "
    "kèm nguồn và thời điểm lấy. Khi công cụ trả thieu=true thì nói rõ là thiếu và lý do, không ước lượng hay nội suy. "
    "Không có danh mục, giao dịch hay định giá cá nhân ở đây."
)
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


def build_server(data_dir: Path | str | None = None) -> MCPServer:
    data = PublicData(data_dir or default_data_dir())
    server = MCPServer(name="dautucophieu-cong-khai", title="Dữ liệu công khai HOSE", instructions=INSTRUCTIONS)

    def tool(fn):
        return server.tool(annotations=READ_ONLY)(fn)

    @tool
    def thong_tin_ma(ma: str) -> dict:
        """Mã có niêm yết HOSE không, ngành ICB và thuộc VN30/VN100 không."""
        return vn_times(data.thong_tin_ma(ma))

    @tool
    def gia_ngay(ma: str, tu_ngay: str | None = None, den_ngay: str | None = None, so_phien: int = 60) -> dict:
        """Giá ngày (mở, cao, thấp, đóng, khối lượng) của một mã hoặc VNINDEX; ngày dạng YYYY-MM-DD; tối đa 500 phiên mới nhất."""
        return vn_times(data.gia_ngay(ma, tu_ngay, den_ngay, so_phien))

    @tool
    def lich_su_gia(ma: str, tu_ngay: str | None = None, den_ngay: str | None = None, mat_do: str = "thang") -> dict:
        """Giá đóng cửa dài hạn từ 2013 của một mã, nghìn đồng: giá ĐÃ điều chỉnh của VNDirect khi kho có (dieu_chinh=true; mat_do "thang"
        lấy phiên cuối mỗi tháng, "ngay" từng phiên, tối đa 800); nếu không, giá chưa điều chỉnh (dieu_chinh=false). Kèm các đợt thưởng,
        cổ tức cổ phiếu, phát hành thêm trong khoảng."""
        return vn_times(data.lich_su_gia(ma, tu_ngay, den_ngay, mat_do))

    @tool
    def dinh_gia_chi_so(chi_so: str = "VNINDEX", ty_le: str = "pe", so_diem: int = 60) -> dict:
        """P/E hoặc P/B theo ngày của VNINDEX hoặc VN30 (nguồn VNDirect); tep_cap_nhat_luc là giờ ứng dụng ghi tệp (UTC)."""
        return vn_times(data.dinh_gia_chi_so(chi_so, ty_le, so_diem))

    @tool
    def bao_cao_tai_chinh(ma: str, ky: str = "quy", so_ky: int = 8) -> dict:
        """Các dòng BCTC (kết quả kinh doanh, cân đối kế toán, lưu chuyển tiền tệ) theo kỳ quy hoặc nam, đơn vị đồng, các kỳ mới nhất;
        ten_dong là tên VNDirect của từng dòng, pham_vi nói dòng nào gồm cổ đông không kiểm soát."""
        return vn_times(data.bao_cao_tai_chinh(ma, ky, so_ky))

    @tool
    def chi_so_tai_chinh(ma: str, so_ky: int = 8) -> dict:
        """Chỉ số tài chính theo quý do VNDirect tính: bộ ngành cho ngân hàng, chứng khoán, bảo hiểm; với doanh nghiệp thường là ROAE, ROIC,
        các biên lợi nhuận, nợ vay/vốn chủ, khả năng trả lãi, số ngày phải thu, tồn kho, phải trả… kèm ten_chi_so là tên VNDirect."""
        return vn_times(data.chi_so_tai_chinh(ma, so_ky))

    @tool
    def eps_co_tuc(ma: str, so_ky: int = 8) -> dict:
        """EPS, LNST công ty mẹ, vốn chủ (gồm thiểu số) theo năm và quý; lợi ích thiểu số cùng kỳ; cổ tức, phát hành, số cổ phiếu lưu hành."""
        return vn_times(data.eps_co_tuc(ma, so_ky))

    @tool
    def dinh_gia_ma(ma: str) -> dict:
        """Vốn hoá, P/E, P/B và số cổ phiếu do VNDirect công bố cho một mã, kèm ngày, quý lợi nhuận, giá ứng với số đó và độ lệch so với giá mới nhất."""
        return vn_times(data.dinh_gia_ma(ma))

    @tool
    def so_sanh_nganh(ma: str) -> dict:
        """Đặt một mã cạnh các doanh nghiệp cùng ngành ICB cấp 2 trên HOSE ở quý mới nhất: 16 chỉ số VNDirect (ROAE, ROIC, biên, nợ vay,
        khả năng trả lãi, thanh toán, dòng tiền, số ngày phải thu và tồn kho, tăng trưởng, trả cổ tức), mỗi chỉ số có trung vị, tứ phân vị
        và thứ hạng; ngân hàng so với các ngân hàng HOSE trên 9 chỉ số (NPL, nợ quá hạn, bao phủ nợ xấu, NIM, LDR, tăng trưởng cho vay,
        vốn chủ/tài sản, ROAA, ROAE); công ty chứng khoán so với các mã HOSE thuộc ICB cấp 4 Dịch vụ đầu tư trên 5 chỉ số (ROAA, ROAE, biên
        lợi nhuận ròng, cho vay/vốn chủ, vốn chủ/tài sản); không cho bảo hiểm."""
        return vn_times(data.so_sanh_nganh(ma))

    @tool
    def thuyet_minh(ma: str, ky: str = "quy", so_ky: int = 4) -> dict:
        """Thuyết minh BCTC (Vietcap): doanh thu và chi phí tài chính theo khoản (lãi tiền gửi, cổ tức, thanh lý đầu tư, tỷ giá, khác),
        nợ vay theo loại, tồn kho theo loại, tài sản cố định, chi phí theo yếu tố; ky "quy" hoặc "nam"."""
        return vn_times(data.thuyet_minh(ma, ky, so_ky))

    @tool
    def dinh_gia_lich_su(ma: str) -> dict:
        """P/E và P/B của chính mã ở mỗi cuối tháng (tự tính từ báo cáo và giá VNDirect): trung vị, tứ phân vị, thấp, cao trong 3 và 5 năm,
        và vị trí hiện tại; để biết P/E hôm nay cao hay thấp so với quá khứ của mã."""
        return vn_times(data.dinh_gia_lich_su(ma))

    @tool
    def su_kien_doanh_nghiep(ma: str) -> dict:
        """Sự kiện doanh nghiệp: cổ tức, phát hành, đại hội cổ đông, ngày chốt quyền."""
        return vn_times(data.su_kien_doanh_nghiep(ma))

    @tool
    def co_dong_ban_lanh_dao(ma: str) -> dict:
        """Cổ đông lớn và ban lãnh đạo đang nắm cổ phiếu."""
        return vn_times(data.co_dong_ban_lanh_dao(ma))

    @tool
    def giao_dich_noi_bo(ma: str) -> dict:
        """Giao dịch của người nội bộ và người liên quan đã công bố; báo cáo nguồn không có số lượng được đánh dấu thieu_so_luong kèm van_ban."""
        return vn_times(data.giao_dich_noi_bo(ma))

    @tool
    def danh_sach_vi_mo() -> dict:
        """Danh sách mã chỉ báo vĩ mô đang có (CPI, PMI, lãi suất, tỷ giá, hàng hóa, chỉ số Mỹ…) kèm trạng thái cập nhật."""
        return vn_times(data.danh_sach_vi_mo())

    @tool
    def chi_bao_vi_mo(ma: str, so_diem: int = 24) -> dict:
        """Các quan sát mới nhất của một chỉ báo vĩ mô; lấy mã từ danh_sach_vi_mo."""
        return vn_times(data.chi_bao_vi_mo(ma, so_diem))

    @tool
    def chi_so_chau_a() -> dict:
        """Các chỉ số chứng khoán châu Á mới nhất."""
        return vn_times(data.chi_so_chau_a())

    @tool
    def gia_vang() -> dict:
        """Giá vàng trong nước mới nhất (mua, bán)."""
        return vn_times(data.gia_vang())

    @tool
    def gia_vang_lich_su(loai: str | None = None, so_ngay: int = 30) -> dict:
        """Lịch sử giá mua vàng trong nước theo ngày (đồng/chỉ, Phú Quý); không kèm loai thì trả danh sách loại vàng."""
        return vn_times(data.gia_vang_lich_su(loai, so_ngay))

    @tool
    def quy_mo(ma: str | None = None, so_ngay: int = 30) -> dict:
        """Quỹ mở trên Fmarket: không kèm ma thì trả danh sách quỹ và NAV mới nhất; có ma thì NAV, hồ sơ (phí, loại, công ty quản lý,
        lợi nhuận công bố), lịch sử NAV và danh mục quỹ đã công bố."""
        return vn_times(data.quy_mo(ma, so_ngay))

    @tool
    def omo(so_phien: int = 5) -> dict:
        """Kết quả nghiệp vụ thị trường mở (OMO) của Ngân hàng Nhà nước, các phiên mới nhất."""
        return vn_times(data.omo(so_phien))

    return server


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()

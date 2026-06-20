/**
 * 站点 Logo（public/logo.svg）。
 */
export default function AppLogo({ size = 32, className = "" }) {
  return (
    <img
      src="/logo.svg"
      alt="Logo"
      width={size}
      height={size}
      className={className}
      draggable={false}
    />
  );
}

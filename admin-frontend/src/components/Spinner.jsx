export default function Spinner({ size = 18 }) {
  const px = typeof size === 'number' ? `${size}px` : size;
  return (
    <span
      className="spinner"
      style={{ width: px, height: px }}
      aria-label="loading"
    />
  );
}

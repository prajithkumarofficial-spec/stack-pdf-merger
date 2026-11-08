pkgname=stack-pdf-merger
pkgver=1.1.0
pkgrel=1
pkgdesc='A local desktop workbench for merging and editing PDF files'
arch=('any')
license=('custom:MIT')
depends=('python' 'pyside6' 'python-pypdf' 'python-cryptography')
source=('app.py' 'stack.desktop' 'LICENSE' 'icon.svg')
sha256sums=('SKIP' 'SKIP' 'SKIP' 'SKIP')

package() {
  install -Dm755 "$srcdir/app.py" "$pkgdir/usr/share/stack-pdf-merger/app.py"
  install -Dm644 "$srcdir/icon.svg" "$pkgdir/usr/share/stack-pdf-merger/icon.svg"
  install -Dm644 "$srcdir/icon.svg" "$pkgdir/usr/share/icons/hicolor/scalable/apps/stack-pdf-merger.svg"
  install -Dm644 "$srcdir/LICENSE" "$pkgdir/usr/share/licenses/stack-pdf-merger/LICENSE"
  install -Dm644 "$srcdir/stack.desktop" "$pkgdir/usr/share/applications/stack-pdf-merger.desktop"
  install -d "$pkgdir/usr/bin"
  cat > "$pkgdir/usr/bin/stack-pdf-merger" <<'EOF'
#!/bin/sh
exec python3 /usr/share/stack-pdf-merger/app.py "$@"
EOF
  chmod 755 "$pkgdir/usr/bin/stack-pdf-merger"
}

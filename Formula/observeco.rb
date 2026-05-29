# typed: true
# frozen_string_literal: true

class Observeco < Formula
  desc "Runtime observability for AI agent systems — pulse, circuit breaker, token compression, dashboard"
  homepage "https://github.com/observeco/observeco"
  url "https://files.pythonhosted.org/packages/f9/ca/7dc7cc39f819be0f9a3a5cab31a372da33645cb2e30b4fc0a0c46b17c57f/observeco-0.1.0.tar.gz"
  sha256 "284c0cd01a9578ed394a025ae12d11762a6de4c9fb8b0daee591a3c5eeb99a94"
  license "MIT"

  depends_on "python@3.12"

  resource "typer" do
    url "https://files.pythonhosted.org/packages/e4/51/9aed62104cea109b820bbd6c14245af756112017d309da813ef107d42e7e/typer-0.25.1.tar.gz"
    sha256 "9616eb8853a09ffeabab1698952f33c6f29ffdbceb4eaeecf571880e8d7664cc"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/b3/c6/f3b320c27991c46f43ee9d856302c70dc2d0fb2dba4842ff739d5f46b393/rich-14.3.3.tar.gz"
    sha256 "b8daa0b9e4eef54dd8cf7c86c03713f53241884e814f4e2f5fb342fe520f639b"
  end

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/b1/df/48c586a5fe32a0f01324ee087459e112ebb7224f646c0b5023f5e79e9956/httpx-0.28.1.tar.gz"
    sha256 "75e98c5f16b0f35b567856f597f06ff2270a374470a5c2392242528e3e3e42fc"
  end

  resource "platformdirs" do
    url "https://files.pythonhosted.org/packages/9f/4a/0883b8e3802965322523f0b200ecf33d31f10991d0401162f4b23c698b42/platformdirs-4.9.6.tar.gz"
    sha256 "3bfa75b0ad0db84096ae777218481852c0ebc6c727b3168c1b9e0118e458cf0a"
  end

  def install
    python3 = "python3.12"
    venv = libexec/"venv"
    system python3, "-m", "venv", venv
    system venv/"bin/pip", "install", "--no-binary=:all:", "pip", "setuptools", "wheel"

    resources.each do |r|
      r.stage do
        system venv/"bin/pip", "install", "-v", "."
      end
    end

    system venv/"bin/pip", "install", "-v", "."

    (bin/"observeco").write_env_script(venv/"bin/observeco", PATH: "#{venv}/bin:$PATH")
  end

  test do
    system "#{bin}/observeco", "--help"
  end
end
